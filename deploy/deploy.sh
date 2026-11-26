#!/bin/bash
# Deploy na EC2. Chamado pelo workflow deploy-aws.yml via SSM Run Command,
# depois de baixar este arquivo, o compose e o Caddyfile do mesmo commit.
#
#     bash deploy.sh <imagem-do-ecr>
#
# Ordem deliberada: a migration roda antes da troca do contêiner. Falhando,
# o script para com a versão anterior ainda no ar.
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

# Os dois arquivos são regenerados a cada deploy, a partir do Parameter
# Store. Trocar um segredo é atualizar o parâmetro e refazer o deploy.
umask 077

cat > .env <<EOF
API_IMAGE=$image
API_DOMAIN=${ip//./-}.sslip.io
AWS_REGION=$region
LOG_GROUP=/cinerini/api
EOF

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

echo "Trocando os contêineres"
$compose up -d --wait

# Imagens antigas ocupam o disco de 10 GB a cada deploy. A anterior continua
# no ECR, que é de onde o rollback a busca.
docker image prune -af --filter "until=24h" > /dev/null

echo "Deploy concluído: $image"
