# Reset diário do ambiente de demonstração: Scheduler → Lambda → SSM na EC2.
#
# Custo zero dentro da cota gratuita: uma invocação por dia de cerca de um
# minuto a 128 MB, contra 1 milhão de invocações e 400 mil GB-segundo
# gratuitos por mês, e 14 milhões de agendamentos gratuitos no Scheduler.

data "archive_file" "reset_demo" {
  type        = "zip"
  source_file = "${path.module}/lambda/reset_demo.py"
  output_path = "${path.module}/.build/reset_demo.zip"
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "reset_demo" {
  name               = "${var.project}-reset-demo"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "reset_demo" {
  # Mesmas restrições da role de deploy: só a instância do projeto, só o
  # documento de shell.
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

  statement {
    sid       = "RunShellDocument"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:${var.region}::document/AWS-RunShellScript"]
  }

  statement {
    sid       = "ReadState"
    actions   = ["ec2:DescribeInstances", "ssm:GetCommandInvocation"]
    resources = ["*"]
  }

  # Log só no próprio grupo, criado abaixo com retenção.
  statement {
    sid       = "WriteLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.reset_demo.arn}:*"]
  }
}

resource "aws_iam_role_policy" "reset_demo" {
  name   = "reset-demo"
  role   = aws_iam_role.reset_demo.id
  policy = data.aws_iam_policy_document.reset_demo.json
}

# Criado antes da função para ter retenção: sem ele, a Lambda cria o grupo
# sozinha, sem prazo, e o log fica cobrando para sempre.
resource "aws_cloudwatch_log_group" "reset_demo" {
  name              = "/aws/lambda/${var.project}-reset-demo"
  retention_in_days = 7
}

resource "aws_lambda_function" "reset_demo" {
  function_name    = "${var.project}-reset-demo"
  role             = aws_iam_role.reset_demo.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "reset_demo.handler"
  filename         = data.archive_file.reset_demo.output_path
  source_code_hash = data.archive_file.reset_demo.output_base64sha256
  memory_size      = 128

  # O seed leva alguns segundos; a espera pelo resultado tem teto de 150.
  timeout = 180

  environment {
    variables = { PROJECT = var.project }
  }

  depends_on = [aws_cloudwatch_log_group.reset_demo, aws_iam_role_policy.reset_demo]
}

data "aws_iam_policy_document" "scheduler_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    # Só agendamentos desta conta assumem a role.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.project}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_trust.json
}

resource "aws_iam_role_policy" "scheduler" {
  name = "invoke-reset-demo"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.reset_demo.arn
    }]
  })
}

resource "aws_scheduler_schedule" "reset_demo" {
  name                         = "${var.project}-reset-demo"
  schedule_expression          = var.demo_reset_cron
  schedule_expression_timezone = "America/Sao_Paulo"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.reset_demo.arn
    role_arn = aws_iam_role.scheduler.arn

    # Uma falha não se repete: rodar o seed de novo no mesmo minuto falharia
    # pelo mesmo motivo, e o alarme abaixo já avisou.
    retry_policy {
      maximum_retry_attempts = 0
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "reset_demo" {
  alarm_name          = "${var.project}-reset-demo-falhou"
  alarm_description   = "O reset diario do ambiente de demonstracao falhou"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.reset_demo.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
