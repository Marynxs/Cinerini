"""Teto de requisições em andamento abaixo das conexões e das threads."""

import anyio

from app.backpressure import MAX_EM_ANDAMENTO
from app.db import MAX_OVERFLOW, POOL_SIZE


def test_teto_abaixo_das_conexoes_e_das_threads() -> None:
    """Fora dessa relação, um pico trava até o tempo limite do pool.

    A dependência de autenticação segura uma conexão enquanto a rota espera
    thread; com as threads todas esperando conexão, ninguém avança. Foi o que
    aconteceu com 500 reservas simultâneas antes do teto.
    """

    async def threads() -> float:
        return anyio.to_thread.current_default_thread_limiter().total_tokens

    assert MAX_EM_ANDAMENTO < POOL_SIZE + MAX_OVERFLOW
    assert MAX_EM_ANDAMENTO < anyio.run(threads)
