variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "cinerini"
}

# EC2 e RDS na mesma zona. A us-east-1e não oferece t4g.
variable "availability_zone" {
  type    = string
  default = "us-east-1a"
}

variable "compose_version" {
  type    = string
  default = "v5.6.1"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/cinerini-aws.pub"
}

# Pessoais, vêm do terraform.tfvars, fora do Git.
variable "admin_cidr" {
  type        = string
  description = "IP de quem administra, com /32. Único autorizado no SSH."
}

variable "alert_email" {
  type        = string
  description = "Recebe os alarmes."
}

# A senha do banco não passa pelo estado, então o Terraform não percebe se
# ela mudar no Parameter Store. Incrementar este número reenvia a senha.
variable "db_password_version" {
  type    = number
  default = 1
}

# Único repositório autorizado a assumir a role de deploy, e só pela main.
variable "github_repo" {
  type    = string
  default = "Marynxs/Cinerini"
}
