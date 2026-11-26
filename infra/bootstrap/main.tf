# Bucket do estado do Terraform de `infra/`.
#
# Separado porque o bucket que guarda o estado não pode estar no estado que
# ele guarda: um `destroy` em `infra/` apagaria o próprio registro do que
# está apagando. Roda uma vez, com estado local, e quase nunca muda.
#
#     cd infra/bootstrap && terraform init && terraform apply
#
# Custo: o estado tem dezenas de KB, menos de um centavo por mês.

terraform {
  required_version = ">= 1.11"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = "cinerini"
      ManagedBy = "terraform-bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}

# O nome de bucket é global entre todas as contas da AWS; o número da conta
# no nome evita colisão sem sorteio.
resource "aws_s3_bucket" "state" {
  bucket = "cinerini-tfstate-${data.aws_caller_identity.current.account_id}"

  # Apagar este bucket apaga o registro de tudo que existe em `infra/`.
  lifecycle {
    prevent_destroy = true
  }
}

# Cada apply guarda uma versão: um estado corrompido ou sobrescrito volta
# para a anterior.
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Versões antigas saem depois de 90 dias; sem isso o histórico cresce para
# sempre.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expira-versoes-antigas"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# O estado carrega IDs e endereços de toda a infraestrutura: nunca em texto
# puro na rede.
resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "SoTLS"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

output "state_bucket" {
  value = aws_s3_bucket.state.bucket
}
