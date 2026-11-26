# Rede: a VPC padrão da conta, sem VPC própria.
#
# Uma VPC dedicada com sub-rede privada exigiria NAT Gateway para a EC2 sair
# para a internet (~US$ 32/mês), mais que todo o resto somado. Na padrão, a
# EC2 fica em sub-rede pública protegida pelo Security Group, e o RDS, mesmo
# nela, não recebe IP público nem aceita conexão de fora da EC2.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Sub-rede da EC2, na mesma zona do RDS: tráfego entre zonas é cobrado e
# soma latência a cada consulta.
data "aws_subnet" "api" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = var.availability_zone
  default_for_az    = true
}

resource "aws_security_group" "api" {
  name        = "${var.project}-api"
  description = "Entrada da API: HTTP e HTTPS publicos, SSH so do administrador"
  vpc_id      = data.aws_vpc.default.id
}

# 80 só serve ao desafio do Let's Encrypt e ao redirecionamento para 443.
# Com lockdown, 80 e 443 passam a aceitar só o administrador: o site sai do
# ar para o mundo e continua acessível para quem investiga. É o botão de
# emergência contra volume, mais rápido e barato que qualquer filtro.
locals {
  web_cidr = var.lockdown ? var.admin_cidr : "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.api.id
  description       = "HTTP: desafio do Let's Encrypt e redirecionamento para HTTPS"
  cidr_ipv4         = local.web_cidr
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.api.id
  description       = "HTTPS: trafego da API"
  cidr_ipv4         = local.web_cidr
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

# Só do IP do administrador. O Session Manager continua sendo o caminho que
# não depende de porta aberta; o SSH fica como alternativa conhecida.
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.api.id
  description       = "SSH so do administrador"
  cidr_ipv4         = var.admin_cidr
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

# Saída livre: baixar imagem do ECR, falar com o SSM, o CloudWatch, o TMDb e
# o IBGE. Restringir por destino exigiria endpoints de VPC, que são pagos.
resource "aws_vpc_security_group_egress_rule" "api_all" {
  security_group_id = aws_security_group.api.id
  description       = "Saida: ECR, SSM, CloudWatch, TMDb e IBGE"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "db" {
  name        = "${var.project}-db"
  description = "Postgres aceita conexao so da EC2 da API"
  vpc_id      = data.aws_vpc.default.id
}

# A origem é o Security Group da API, e não um IP: vale para qualquer
# instância que o carregue, inclusive uma recriada com outro endereço, e para
# nenhuma outra máquina da VPC.
resource "aws_vpc_security_group_ingress_rule" "db_from_api" {
  security_group_id            = aws_security_group.db.id
  description                  = "Postgres so da EC2 da API"
  referenced_security_group_id = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
