"""Estados e municípios, vindos do IBGE.

Existe por um defeito concreto: cidade e UF eram texto livre, e o filtro do
catálogo agrupa cinemas por cidade. "São Paulo" e "sao paulo" viravam duas
cidades na lista, e nenhuma validação de formato pega isso, porque as duas são
strings perfeitamente válidas.

A UF não vem da rede. São 27 e não mudam desde 1988; buscá-las seria trocar
uma constante por um ponto de falha. Município vem do IBGE porque são 5.570 e
mudam de vez em quando.

O código do município é guardado junto do nome porque **nome de cidade não é
único no Brasil**: existem dezenas de "Bom Jesus", "Santa Luzia" e "Bonito"
em estados diferentes. Agrupar o catálogo por nome juntaria cidades que não
têm nada a ver uma com a outra.
"""

from typing import Any

import httpx
from fastapi import HTTPException, status

BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

# Prazo longo e sem teto de entradas, ao contrário do cache do TMDb: a chave
# aqui é a UF, então o dicionário tem no máximo 27 posições e não cresce com
# o que o usuário digita. Um dia cobre qualquer jornada de cadastro.
CACHE_TTL_SECONDS = 24 * 60 * 60

UFS: list[dict[str, str]] = [
    {"sigla": "AC", "nome": "Acre"},
    {"sigla": "AL", "nome": "Alagoas"},
    {"sigla": "AP", "nome": "Amapá"},
    {"sigla": "AM", "nome": "Amazonas"},
    {"sigla": "BA", "nome": "Bahia"},
    {"sigla": "CE", "nome": "Ceará"},
    {"sigla": "DF", "nome": "Distrito Federal"},
    {"sigla": "ES", "nome": "Espírito Santo"},
    {"sigla": "GO", "nome": "Goiás"},
    {"sigla": "MA", "nome": "Maranhão"},
    {"sigla": "MT", "nome": "Mato Grosso"},
    {"sigla": "MS", "nome": "Mato Grosso do Sul"},
    {"sigla": "MG", "nome": "Minas Gerais"},
    {"sigla": "PA", "nome": "Pará"},
    {"sigla": "PB", "nome": "Paraíba"},
    {"sigla": "PR", "nome": "Paraná"},
    {"sigla": "PE", "nome": "Pernambuco"},
    {"sigla": "PI", "nome": "Piauí"},
    {"sigla": "RJ", "nome": "Rio de Janeiro"},
    {"sigla": "RN", "nome": "Rio Grande do Norte"},
    {"sigla": "RS", "nome": "Rio Grande do Sul"},
    {"sigla": "RO", "nome": "Rondônia"},
    {"sigla": "RR", "nome": "Roraima"},
    {"sigla": "SC", "nome": "Santa Catarina"},
    {"sigla": "SP", "nome": "São Paulo"},
    {"sigla": "SE", "nome": "Sergipe"},
    {"sigla": "TO", "nome": "Tocantins"},
]

SIGLAS = {uf["sigla"] for uf in UFS}

_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def clear_cache() -> None:
    _cache.clear()


def _agora() -> float:
    import time
    return time.monotonic()


def municipios(uf: str) -> list[dict[str, Any]]:
    """Municípios de uma UF, como `{"id": 3550308, "nome": "São Paulo"}`."""
    uf = uf.upper()
    if uf not in SIGLAS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "UF desconhecida.")

    guardado = _cache.get(uf)
    if guardado and _agora() - guardado[0] < CACHE_TTL_SECONDS:
        return guardado[1]

    try:
        resposta = httpx.get(f"{BASE_URL}/estados/{uf}/municipios", timeout=10)
        resposta.raise_for_status()
    except httpx.HTTPError:
        # O IBGE fora do ar não pode impedir o cadastro de cinema: quem já
        # tem a lista em cache continua, e quem não tem recebe um erro que
        # diz o que aconteceu em vez de um 500 mudo.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Não foi possível consultar a lista de municípios do IBGE. "
            "Tente de novo em instantes.",
        )

    lista = [{"id": m["id"], "nome": m["nome"]} for m in resposta.json()]
    lista.sort(key=lambda m: m["nome"])
    _cache[uf] = (_agora(), lista)
    return lista


def resolver(uf: str, city_id: int) -> str:
    """Confirma que o município pertence à UF e devolve o nome oficial.

    O nome vem daqui e nunca do corpo da requisição: aceitar o texto enviado
    pelo cliente reabriria a porta que este módulo existe para fechar.
    """
    for m in municipios(uf):
        if m["id"] == city_id:
            return m["nome"]

    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Este município não pertence à UF informada.",
    )
