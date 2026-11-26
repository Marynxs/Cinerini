"""Limite de tentativas por janela deslizante.

Em memória e não em banco: gravar uma linha por tentativa transformaria cada
requisição numa escrita, e um atacante encheria o disco só insistindo. O
preço é que a contagem zera quando o processo reinicia, o que acontece a cada
deploy. É mitigação de custo, não garantia: encarece o ataque em massa sem
prometer bloqueio absoluto.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import get_settings


class SlidingWindow:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        cutoff = now - self.window
        while hits and hits[0] < cutoff:
            hits.popleft()
        if not hits:
            # Não deixa a chave vazia acumulando: sem isso, cada IP que já
            # passou por aqui ficaria na memória para sempre.
            del self._hits[key]
            return self._hits[key]
        return hits

    def check(self, key: str) -> int:
        """Registra a tentativa. Devolve 0 se permitida, ou os segundos a esperar."""
        now = time.monotonic()
        hits = self._prune(key, now)

        if len(hits) >= self.limit:
            return max(1, int(self.window - (now - hits[0])))

        hits.append(now)
        return 0

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        self._hits.clear()


def client_ip(request: Request) -> str:
    """IP do cliente, considerando o proxy quando há um na frente.

    X-Forwarded-For é forjável por quem fala direto com a aplicação, então só
    é lido quando a configuração declara que existe um proxy confiável à
    frente, que em produção é o Caddy, e sobrescreve o cabeçalho.
    """
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


# Registradas por escopo em vez de fechadas dentro da factory: sem isto não
# há como zerar uma janela específica em teste.
_windows: dict[str, SlidingWindow] = {}


def rate_limit(limit: int, window_seconds: int, scope: str):
    """Dependency que limita tentativas por IP numa rota."""
    window = _windows.setdefault(scope, SlidingWindow(limit, window_seconds))

    def guard(request: Request) -> None:
        wait = window.check(f"{scope}:{client_ip(request)}")
        if wait:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Aguarde alguns instantes e tente de novo.",
                headers={"Retry-After": str(wait)},
            )

    return guard


# Por conta, não por IP: sem isto, um atacante com muitos IPs testaria senhas
# de uma mesma conta sem nunca esbarrar no limite de rede. É esta janela que
# defende de fato contra força bruta de senha, e a de IP existe para encarecer
# varredura em massa, e por isso é folgada.
login_by_account = SlidingWindow(limit=8, window_seconds=900)


class PerMinute:
    """Teto de requisições por IP em cada minuto do relógio.

    Contador por chave, e não a lista de horários da janela deslizante: sob
    varredura distribuída, milhares de IPs com trezentos horários cada
    esgotariam a memória de uma instância de 1 GB. Aqui cada IP custa um
    inteiro, e tudo é descartado quando o minuto vira. O preço é a borda: um
    cliente pode somar dois tetos na virada do minuto, o que não muda a ordem
    de grandeza do que passa.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._minute = -1
        self._counts: dict[str, int] = {}

    def check(self, key: str) -> int:
        """Devolve 0 se permitida, ou os segundos até o próximo minuto."""
        now = time.time()
        minute = int(now // 60)
        if minute != self._minute:
            self._minute = minute
            self._counts = {}

        count = self._counts.get(key, 0) + 1
        self._counts[key] = count
        if count > self.limit:
            return max(1, 60 - int(now % 60))
        return 0

    def clear(self) -> None:
        self._counts = {}


per_ip_minute = PerMinute(limit=get_settings().requests_per_minute)

# A verificação de saúde vem da própria instância a cada minuto e do Docker a
# cada dez segundos; contada, ela ocuparia o teto do IP da máquina.
_SEM_TETO = {"/health"}


async def limit_per_ip(request: Request, call_next) -> Response:
    if request.url.path not in _SEM_TETO:
        wait = per_ip_minute.check(client_ip(request))
        if wait:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Muitas requisições. Aguarde alguns instantes."},
                headers={"Retry-After": str(wait)},
            )
    return await call_next(request)


def clear_all() -> None:
    """Zera todas as janelas. Usado por testes."""
    for window in _windows.values():
        window.clear()
    login_by_account.clear()
    per_ip_minute.clear()
