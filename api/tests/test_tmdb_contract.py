"""Contrato com o TMDb: a resposta real ainda tem o formato esperado.

Bate na API de verdade, e por isso fica fora da execução padrão. O resto da
suíte usa um TMDb falso — teste que depende de rede é lento, quebra sem
internet e falha para quem não tem chave própria, tudo sem que o código
tenha mudado.

O custo de mockar é que o falso concorda comigo por definição: se o TMDb
mudar o formato, os testes falsos continuam verdes. Estes testes existem
para pegar exatamente isso.

    pytest -m contract        roda só estes
    pytest                    roda todo o resto
"""

import pytest

from app.config import get_settings
from app.tmdb import clear_cache, movie_details, search_movies

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(
        not get_settings().tmdb_api_key,
        reason="TMDB_API_KEY não configurada",
    ),
]

# Filme lançado e consagrado: a ficha não sai do catálogo nem muda de forma.
# Escolhido de propósito em vez de lançamento recente, que sairia de cartaz.
INCEPTION = 27205


@pytest.fixture(autouse=True)
def sem_cache() -> None:
    clear_cache()


def test_search_returns_the_fields_we_map() -> None:
    resultados = search_movies("inception")

    assert resultados, "busca por título consagrado não devolveu nada"
    primeiro = resultados[0]
    assert isinstance(primeiro["tmdb_id"], int)
    assert primeiro["title"]


def test_details_return_the_fields_we_store() -> None:
    """Estes campos vão para a tabela events na publicação."""
    ficha = movie_details(INCEPTION)

    assert ficha["tmdb_id"] == INCEPTION
    assert ficha["title"]
    assert ficha["synopsis"]
    assert ficha["runtime_minutes"] > 0
    assert ficha["poster_url"].startswith("https://image.tmdb.org/")
    assert ficha["backdrop_url"].startswith("https://image.tmdb.org/")


def test_response_comes_in_portuguese() -> None:
    """A sinopse é exibida ao cliente; inglês passaria despercebido em teste
    falso e apareceria na tela."""
    ficha = movie_details(INCEPTION)

    assert ficha["title"] == "A Origem"
