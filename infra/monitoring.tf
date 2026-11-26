# Logs, alarmes e o aviso por e-mail.

# Criado aqui, e não pelo Docker, para que a retenção seja definida: sem ela
# o CloudWatch guarda log para sempre e cobra por isso.
resource "aws_cloudwatch_log_group" "api" {
  name              = "/${var.project}/api"
  retention_in_days = 7
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alertas"
}

# A AWS manda um e-mail de confirmação; até alguém clicar no link, nenhum
# alarme chega.
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# A AWS já recupera sozinha a instância quando o hardware falha. O alarme
# serve para alguém saber que aconteceu.
resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "${var.project}-ec2-status"
  alarm_description   = "Falha na verificacao de status da EC2 da API"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.api.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Quinze minutos e não um pico: build de imagem ou rajada de acesso passam
# do limite por instantes sem ser problema. Sustentado, numa t4g com
# créditos fixos, significa que os créditos acabaram e a API ficou lenta.
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "${var.project}-ec2-cpu"
  alarm_description   = "CPU da EC2 da API acima de 80% por 15 minutos"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.api.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Métrica publicada pela própria instância a cada minuto. Ausência de dado
# conta como falha: se a máquina parou, o silêncio é o sintoma.
resource "aws_cloudwatch_metric_alarm" "health" {
  alarm_name          = "${var.project}-api-health"
  alarm_description   = "GET /health por HTTPS falhando por 3 minutos"
  namespace           = "Cinerini"
  metric_name         = "HealthCheck"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
