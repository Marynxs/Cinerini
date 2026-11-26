#!/bin/bash
# Deploy na EC2. Chamado pelo workflow deploy-aws.yml via SSM Run Command,
# depois de baixar este arquivo, o compose e o Caddyfile do mesmo commit.
#
#     bash deploy.sh <imagem-do-ecr>
#
# Ordem deliberada: a migration roda antes da troca do contêiner. Falhando,
# o script para com a versão anterior ainda no ar. Se a versão nova sobe mas
# não responde por HTTPS, o script volta sozinho para a imagem anterior.
set -euo pipefail

image="$1"
region="us-east-1"
compose="docker compose -f docker-compose.prod.yml"

cd /opt/cinerini

param() {
  aws ssm get-parameter --region "$region" --name "/cinerini/$1" \
    --with-decryption --query Parameter.Value --output text
}

# O domínio sai do IP público da própria máquina, o mesmo que o Terraform
# publica: <ip-com-hifens>.sslip.io.
token=$(curl -s -X PUT http://169.254.169.254/latest/api/token \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
ip=$(curl -s -H "X-aws-ec2-metadata-token: $token" \
  http://169.254.169.254/latest/meta-data/public-ipv4)

domain="${ip//./-}.sslip.io"

# Lido antes de o .env ser reescrito: é para esta imagem que o rollback volta.
# Vazio no primeiro deploy da máquina, quando não há para onde voltar.
previous=""
if [ -f .env ]; then
  previous=$(sed -n 's/^API_IMAGE=//p' .env)
fi

# Os dois arquivos são regenerados a cada deploy, a partir do Parameter
# Store. Trocar um segredo é atualizar o parâmetro e refazer o deploy.
umask 077

write_env() {
  cat > .env <<EOF
API_IMAGE=$1
API_DOMAIN=$domain
AWS_REGION=$region
LOG_GROUP=/cinerini/api
EOF
}

write_env "$image"

# A senha é gerada só com letras, números, - e _, e por isso entra na URL
# sem escape.
cat > .env.api <<EOF
DATABASE_URL=postgresql+psycopg://cinerini:$(param db-password)@$(param db-host):5432/cinerini?sslmode=require
SECRET_KEY=$(param secret-key)
TMDB_API_KEY=$(param tmdb-api-key)
CORS_ORIGINS=$(param cors-origins)
EOF

aws ecr get-login-password --region "$region" \
  | docker login --username AWS --password-stdin "${image%%/*}"

echo "Baixando $image"
$compose pull api

echo "Aplicando migrations"
$compose run --rm api alembic upgrade head

# Saúde vista de fora, pelo domínio público: cobre certificado, Caddy e API.
# O healthcheck do contêiner sozinho aprovaria uma API que responde para
# dentro e está inalcançável para quem usa.
healthy() {
  curl -fsS --max-time 5 --retry 6 --retry-delay 5 --retry-all-errors \
    "https://$domain/health" > /dev/null
}

echo "Trocando os contêineres"
if $compose up -d --wait && healthy; then
  # Imagens antigas ocupam o disco de 10 GB a cada deploy. A anterior
  # continua no ECR, de onde um rollback manual a busca.
  docker image prune -af --filter "until=24h" > /dev/null
  echo "Deploy concluído: $image"
  exit 0
fi

echo "A versão nova não respondeu em https://$domain/health" >&2
if [ -z "$previous" ] || [ "$previous" = "$image" ]; then
  echo "Sem versão anterior para onde voltar." >&2
  exit 1
fi

# A migration não volta junto: o schema fica na versão nova. Por isso a regra
# de migration compatível com o código anterior (docs/deploy-aws.md).
echo "Voltando para $previous" >&2
write_env "$previous"
$compose up -d --wait
healthy && echo "Rollback concluído: $previous no ar." >&2
exit 1
