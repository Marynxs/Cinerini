from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backpressure import limit_in_flight
from app.config import get_settings
from app.ratelimit import limit_per_ip
from app.request_log import configure_json_logging, log_request
from app.routers import (
    auth, bookings, catalog, events, gate, sharing, showings, venues,
)

settings = get_settings()

app = FastAPI(
    title="Cinerini",
    description="Plataforma de eventos e ingressos.",
    version="0.1.0",
)

if settings.log_json:
    configure_json_logging()

# O Starlette envolve na ordem inversa do registro: o primeiro fica por
# dentro. O teto de requisições em andamento é o mais interno, para que a
# fila dele só receba quem já passou pelo teto por IP. O teto por IP fica
# dentro do CORS para que o 429 saia com os cabeçalhos de CORS, senão o
# navegador o mostraria como erro de rede.
app.middleware("http")(limit_in_flight)
app.middleware("http")(limit_per_ip)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrado depois do CORS, e por isso por fora dele: o Starlette envolve na
# ordem inversa do registro. Assim o preflight também é medido e registrado.
app.middleware("http")(log_request)


app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(venues.router)
app.include_router(events.router)
app.include_router(showings.router)
app.include_router(bookings.router)
app.include_router(sharing.router)
app.include_router(gate.router)


@app.get("/", tags=["infra"], summary="Porta de entrada da API")
def raiz() -> dict[str, str]:
    """Existe porque a raiz de um serviço é o que as pessoas digitam.

    Sem esta rota, abrir o endereço da API devolvia `404 Not Found`, tecnicamente
    correto e inútil: quem chegou ali não sabe se errou o endereço, se o
    serviço caiu, ou se é assim mesmo. Este corpo diz o que é e para onde ir.

    Não redireciona para `/docs` de propósito: redirecionar esconderia que a
    raiz não serve interface, e quem estivesse conferindo o serviço por
    script receberia um 307 no lugar de uma resposta.
    """
    return {
        "servico": "API do Cinerini",
        "documentacao": "/docs",
        "contrato": "/openapi.json",
        "saude": "/health",
        "site": "https://cinerini.vercel.app",
    }


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
