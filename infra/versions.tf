# Infraestrutura da API na AWS.
#
#     terraform init       uma vez, baixa o provider
#     terraform plan       mostra o que mudaria, sem mudar
#     terraform apply      aplica
#     terraform destroy    apaga tudo o que está aqui
#
# O estado fica no S3, versionado e com trava (ver o backend abaixo e
# `bootstrap/`). Perdê-lo não apaga nada na AWS, mas faz o Terraform esquecer
# o que criou: os recursos seguem cobrando e passam a ter de ser removidos à
# mão.

terraform {
  required_version = ">= 1.11"

  # Estado no S3, criado por `bootstrap/`. A trava é um objeto .tflock ao
  # lado do estado: dois applies simultâneos, de duas máquinas ou de um
  # terminal esquecido aberto, não sobrescrevem um ao outro. Sem DynamoDB,
  # que o Terraform 1.10 tornou dispensável.
  backend "s3" {
    bucket       = "cinerini-tfstate-618042349946"
    key          = "infra/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region = var.region

  # Toda peça criada daqui sai marcada. É o que permite filtrar o custo do
  # projeto no Cost Explorer e achar sobra esquecida depois de um destroy.
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}
