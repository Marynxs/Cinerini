# Imagem da API.
#
# Base Debian e não Alpine por um motivo concreto: `psycopg[binary]` publica
# wheel para glibc, não para musl. Em Alpine o pip cairia para compilar o
# driver do zero, exigindo toolchain e cabeçalhos do libpq: minutos de build
# e uma dependência de sistema a mais para manter.
FROM python:3.14-slim

# Sem .pyc e sem buffer na saída: em contêiner o log é a única janela, e
# saída presa em buffer chega tarde ou não chega.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# A imagem oficial é republicada de tempos em tempos, e entre uma publicação e
# outra o Debian corrige pacotes do sistema. Aplicar as atualizações aqui fecha
# essa janela sem esperar a próxima base.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# As dependências entram antes do código para que o cache de camada sobreviva
# a qualquer alteração em `app/`. Só mudar `requirements.txt` reinstala.
COPY requirements.txt .
#
# O pip sai depois de instalar: em execução ninguém instala nada, e ele traz
# cópias próprias de urllib3, msgpack e setuptools que o scanner de
# vulnerabilidades acusa sem que a aplicação jamais as carregue.
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y pip

COPY . .

EXPOSE 8000

# `sh` explícito em vez de depender do bit de execução: o repositório é
# clonado no Windows, que não guarda permissão de arquivo, e o contêiner
# recusaria a subir com "permission denied".
CMD ["sh", "docker-entrypoint.sh"]
