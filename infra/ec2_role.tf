# O que a própria instância pode fazer na AWS.
#
# Sem chave de acesso em disco: a EC2 recebe credenciais temporárias desta
# role pelo serviço de metadados, renovadas sozinhas.

data "aws_iam_policy_document" "ec2_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2" {
  name               = "${var.project}-ec2"
  assume_role_policy = data.aws_iam_policy_document.ec2_trust.json
}

# Session Manager e Run Command: é por aqui que o deploy chega à máquina e
# que se abre um terminal nela sem porta 22.
resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "ec2_runtime" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Só baixar, e só a imagem da API.
  statement {
    sid = "EcrPull"
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.api.arn]
  }

  # Ler os segredos do projeto, e nenhum outro parâmetro da conta. A chave
  # KMS é a gerenciada pela AWS (aws/ssm), cuja política já autoriza quem
  # chega pelo SSM; não precisa de permissão de KMS aqui.
  statement {
    sid = "ReadSecrets"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = [
      "arn:aws:ssm:${var.region}:${local.account_id}:parameter/${var.project}",
      "arn:aws:ssm:${var.region}:${local.account_id}:parameter/${var.project}/*",
    ]
  }

  # Escrever log só no grupo do projeto. O grupo é criado pelo Terraform, e
  # por isso o Docker não recebe permissão de criar grupos.
  statement {
    sid = "WriteLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = [
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:/${var.project}/*",
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:/${var.project}/*:log-stream:*",
    ]
  }
}

resource "aws_iam_role_policy" "ec2_runtime" {
  name   = "runtime"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.ec2_runtime.json
}

# A EC2 não recebe a role direto: recebe este "perfil", que a carrega.
resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project}-ec2"
  role = aws_iam_role.ec2.name
}
