# A máquina da API: Docker com a API e o Caddy.

# Amazon Linux 2023 para ARM, resolvido na hora do primeiro apply. Já traz o
# agente do SSM e a AWS CLI, que o deploy usa.
data "aws_ssm_parameter" "al2023_arm" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_key_pair" "admin" {
  key_name   = "${var.project}-admin"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

resource "aws_instance" "api" {
  ami                    = data.aws_ssm_parameter.al2023_arm.value
  instance_type          = "t4g.micro"
  subnet_id              = data.aws_subnet.api.id
  vpc_security_group_ids = [aws_security_group.api.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  key_name               = aws_key_pair.admin.key_name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region          = var.region
    compose_version = var.compose_version
  })

  # Só o token de sessão do IMDSv2 dá acesso às credenciais da role. Sem
  # isso, uma falha de SSRF na aplicação bastaria para lê-las.
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 10
    encrypted   = true
  }

  # Créditos de CPU fixos: no modo "unlimited", padrão das t4g, um pico
  # prolongado vira cobrança extra em vez de lentidão.
  credit_specification {
    cpu_credits = "standard"
  }

  tags = {
    Name = "${var.project}-api"
  }

  # Uma AMI nova é publicada a cada poucas semanas. Sem isto, todo apply
  # depois disso recriaria a máquina. A atualização do sistema fica com o
  # dnf, e a troca de AMI vira decisão explícita. O user_data roda só no
  # primeiro boot, então mudá-lo numa máquina existente não teria efeito.
  lifecycle {
    ignore_changes = [ami, user_data]
  }
}

# IP fixo: o domínio sslip.io é o próprio IP, e o certificado é emitido para
# ele. Sem IP elástico, parar e ligar a máquina trocaria o endereço, e com
# ele o domínio, o certificado e a URL configurada no front.
resource "aws_eip" "api" {
  instance = aws_instance.api.id
  domain   = "vpc"
}
