# Painel da API e o SLO de disponibilidade.
#
# SLO: 99% dos minutos com GET /health respondendo por HTTPS, em 30 dias.
# Orçamento de erro: 1% de 43.200 minutos, 432 minutos (7h12) por mês.
# A fonte é a métrica que a instância publica a cada minuto; minuto sem dado
# conta como indisponível, a mesma regra do alarme de saúde.

locals {
  slo_target = 99

  # Logs Insights sobre a linha JSON que app/request_log.py escreve.
  q_latencia = <<-EOT
    SOURCE '${aws_cloudwatch_log_group.api.name}'
    | filter logger = "cinerini.request"
    | stats count(*) as requisicoes, pct(duration_ms, 50) as p50,
            pct(duration_ms, 95) as p95, pct(duration_ms, 99) as p99 by route
    | sort requisicoes desc
  EOT

  q_status = <<-EOT
    SOURCE '${aws_cloudwatch_log_group.api.name}'
    | filter logger = "cinerini.request"
    | fields floor(status / 100) * 100 as classe
    | stats count(*) as requisicoes by bin(5m), classe
  EOT
}

resource "aws_cloudwatch_dashboard" "api" {
  dashboard_name = var.project

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "text", x = 0, y = 0, width = 24, height = 2
        properties = {
          markdown = "## Cinerini · API\nSLO: **${local.slo_target}%** dos minutos com `/health` respondendo por HTTPS em 30 dias. Orçamento de erro: **432 minutos por mês** (7h12). Minuto sem dado conta como indisponível."
        }
      },
      {
        # Disponibilidade no intervalo escolhido no painel: minutos bons
        # divididos pelos minutos que o intervalo tem, e não pelos minutos
        # que chegaram, para que o silêncio conte contra.
        type = "metric", x = 0, y = 2, width = 8, height = 6
        properties = {
          title                = "Disponibilidade (SLO ${local.slo_target}%)"
          view                 = "singleValue"
          region               = var.region
          setPeriodToTimeRange = true
          metrics = [
            ["Cinerini", "HealthCheck", { id = "ok", stat = "Sum", visible = false }],
            [{ expression = "100 * ok / (PERIOD(ok) / 60)", label = "Disponibilidade %", id = "disp" }],
          ]
        }
      },
      {
        type = "metric", x = 8, y = 2, width = 16, height = 6
        properties = {
          title  = "Saúde por HTTPS (1 = respondendo)"
          view   = "timeSeries"
          region = var.region
          period = 60
          stat   = "Minimum"
          yAxis  = { left = { min = 0, max = 1 } }
          metrics = [
            ["Cinerini", "HealthCheck", { id = "h", visible = false }],
            [{ expression = "FILL(h, 0)", label = "HealthCheck", id = "hf" }],
          ]
        }
      },
      {
        type = "log", x = 0, y = 8, width = 24, height = 7
        properties = {
          title  = "Latência por rota (ms)"
          region = var.region
          query  = local.q_latencia
          view   = "table"
        }
      },
      {
        type = "log", x = 0, y = 15, width = 12, height = 6
        properties = {
          title   = "Requisições por classe de status"
          region  = var.region
          query   = local.q_status
          view    = "bar"
          stacked = true
        }
      },
      {
        type = "metric", x = 12, y = 15, width = 12, height = 6
        properties = {
          title  = "EC2: CPU e créditos"
          view   = "timeSeries"
          region = var.region
          period = 300
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.api.id, { stat = "Average", label = "CPU %" }],
            ["AWS/EC2", "CPUCreditBalance", "InstanceId", aws_instance.api.id, { stat = "Average", label = "Créditos", yAxis = "right" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 21, width = 24, height = 6
        properties = {
          title  = "RDS"
          view   = "timeSeries"
          region = var.region
          period = 300
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.identifier, { stat = "Average", label = "CPU %" }],
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", aws_db_instance.main.identifier, { stat = "Maximum", label = "Conexões" }],
            ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", aws_db_instance.main.identifier, { stat = "Minimum", label = "Disco livre (bytes)", yAxis = "right" }],
          ]
        }
      },
    ]
  })
}

# Erro de servidor contado a partir da linha JSON. O filtro de métrica é
# gratuito; a métrica gerada custa como qualquer métrica customizada, cerca
# de US$ 0,30 por mês.
resource "aws_cloudwatch_log_metric_filter" "errors_5xx" {
  name           = "${var.project}-5xx"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.logger = \"cinerini.request\" && $.status >= 500 }"

  metric_transformation {
    name          = "Errors5xx"
    namespace     = "Cinerini"
    value         = "1"
    default_value = "0"
  }
}

# Cinco erros em cinco minutos, e não um: uma falha isolada vira e-mail
# toda vez, e e-mail frequente deixa de ser lido.
resource "aws_cloudwatch_metric_alarm" "errors_5xx" {
  alarm_name          = "${var.project}-api-5xx"
  alarm_description   = "Cinco ou mais respostas 5xx em 5 minutos"
  namespace           = "Cinerini"
  metric_name         = "Errors5xx"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

output "dashboard_url" {
  value = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards/dashboard/${aws_cloudwatch_dashboard.api.dashboard_name}"
}
