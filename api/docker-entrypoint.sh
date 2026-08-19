#!/bin/sh
# Migration e seed antes do servidor: o objetivo do Compose é que um clone
# limpo suba com dados percorríveis, e não que peça mais dois comandos.
set -e

echo "Aplicando migrations..."
alembic upgrade head

# Idempotente: já semeado, não faz nada. É o que permite chamá-lo em toda
# subida sem duplicar o catálogo.
echo "Semeando..."
python -m app.seed

# `exec` para que o uvicorn vire o PID 1 e receba o sinal de parada direto.
# Sem isso o `docker compose down` esperaria o timeout e mataria à força.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
