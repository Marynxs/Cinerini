"""Teto de requisições em andamento, para o pool de conexões não travar.

O FastAPI roda código síncrono em 40 threads, e cada requisição atravessa
mais de uma: a dependência que autentica já consulta o banco, e com isso
segura uma conexão, e a rota precisa de outra thread para continuar. Sem
teto, um pico deixa requisições segurando todas as conexões à espera de
thread, e as threads todas à espera de conexão. Nada anda até o tempo limite
do pool, e tudo vira 500. Foi o que 500 reservas simultâneas produziram
(loadtest/corrida.js).

Com no máximo MAX_EM_ANDAMENTO requisições dentro da aplicação, abaixo tanto
das conexões quanto das threads, toda requisição admitida encontra as duas
livres. As demais esperam aqui, antes de tocar no banco, sem segurar nada.
"""

import asyncio

from fastapi import Request, Response

from app.db import MAX_OVERFLOW, POOL_SIZE

MAX_EM_ANDAMENTO = 30

# Conferido na importação, e não só em teste: um ajuste no pool que quebre a
# relação travaria a produção no primeiro pico, sem nenhum erro antes disso.
assert MAX_EM_ANDAMENTO < POOL_SIZE + MAX_OVERFLOW

_vagas = asyncio.Semaphore(MAX_EM_ANDAMENTO)


async def limit_in_flight(request: Request, call_next) -> Response:
    async with _vagas:
        return await call_next(request)
