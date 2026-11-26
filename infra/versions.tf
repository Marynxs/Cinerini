# Infraestrutura da API na AWS.
#
#     terraform init       uma vez, baixa o provider
#     terraform plan       mostra o que mudaria, sem mudar
#     terraform apply      aplica
#     terraform destroy    apaga tudo o que está aqui
#
# O estado fica local, em terraform.tfstate, fora do Git. Perdê-lo não apaga
# nada na AWS, mas faz o Terraform esquecer o que criou: os recursos seguem
# cobrando e passam a ter de ser removidos à mão.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
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
