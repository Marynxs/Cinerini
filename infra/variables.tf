variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "cinerini"
}

# Único repositório autorizado a assumir a role de deploy, e só pela main.
variable "github_repo" {
  type    = string
  default = "Marynxs/Cinerini"
}
