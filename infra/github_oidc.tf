# Deploy pelo GitHub Actions sem chave de acesso guardada.
#
# O workflow recebe do GitHub um token assinado, válido por minutos, que diz
# de qual repositório e branch ele vem. A AWS confere a assinatura contra
# este provedor e devolve credenciais temporárias da role abaixo. Não existe
# segredo da AWS no GitHub para vazar.

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Igualdade exata, nunca curinga: só a main deste repositório. Um fork,
    # outra branch ou um pull request recebem token com outro `sub` e são
    # recusados.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name                 = "${var.project}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "github_deploy" {
  # O login no ECR não aceita recurso específico: a AWS só o define sobre "*".
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Enviar imagem, e só para o repositório da API.
  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
      "ecr:BatchGetImage",
    ]
    resources = [aws_ecr_repository.api.arn]
  }

  # Mandar comando só para instância marcada com o projeto. A instância é
  # recriável e o ID muda; a tag não.
  statement {
    sid       = "RunOnProjectInstance"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ec2:${var.region}:${local.account_id}:instance/*"]

    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/Project"
      values   = [var.project]
    }
  }

  # E só o documento que executa shell, que é o que o deploy usa.
  statement {
    sid       = "RunShellDocument"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:${var.region}::document/AWS-RunShellScript"]
  }

  # Leitura: achar a instância pela tag e acompanhar o resultado do comando.
  # Nenhuma das três aceita recurso específico.
  statement {
    sid = "ReadDeployState"
    actions = [
      "ec2:DescribeInstances",
      "ssm:GetCommandInvocation",
      "ssm:ListCommandInvocations",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "deploy"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}
