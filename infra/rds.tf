# Banco gerenciado. Backup, atualização menor e troca de disco são da AWS.

resource "aws_db_subnet_group" "main" {
  name       = var.project
  subnet_ids = data.aws_subnets.default.ids
}

# A senha é lida do Parameter Store sem passar pelo estado do Terraform:
# `ephemeral` existe só durante o apply, e `password_wo` é um atributo de
# escrita que o provider envia à AWS e nunca grava. Com `password` comum, ela
# ficaria em texto puro no terraform.tfstate.
ephemeral "aws_ssm_parameter" "db_password" {
  arn             = "arn:aws:ssm:${var.region}:${local.account_id}:parameter/${var.project}/db-password"
  with_decryption = true
}

resource "aws_db_instance" "main" {
  identifier     = var.project
  engine         = "postgres"
  engine_version = "18"
  instance_class = "db.t4g.micro"

  # Mesma zona da EC2. Multi-AZ dobraria o custo para proteger contra a
  # queda de uma zona, risco que uma instância de EC2 única já não cobre.
  availability_zone = var.availability_zone
  multi_az          = false

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.project
  username = var.project

  password_wo         = ephemeral.aws_ssm_parameter.db_password.value
  password_wo_version = var.db_password_version

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  # O plano gratuito da conta recusa retenção maior que um dia
  # (FreeTierRestrictionError). Ainda permite restaurar para qualquer minuto
  # das últimas 24 horas; com plano pago, o valor pode subir até 35.
  backup_retention_period    = 1
  auto_minor_version_upgrade = true
  apply_immediately          = true

  # O destroy precisa apagar tudo de uma vez: um snapshot final continuaria
  # cobrando depois de o projeto sair do ar, e os dados são do seed.
  skip_final_snapshot = true
  deletion_protection = false
}

# O endereço do banco não é segredo, mas o deploy precisa dele para montar a
# DATABASE_URL. Publicado ao lado dos segredos, o script lê tudo de um lugar.
resource "aws_ssm_parameter" "db_host" {
  name  = "/${var.project}/db-host"
  type  = "String"
  value = aws_db_instance.main.address
}
