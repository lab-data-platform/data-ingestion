# Lambda do CDI diário: código em functions/bcb_cdi/handler.py.
# Recursos: zip do código, log group, role com permissão mínima, a função e a agenda.

locals {
  cdi_name   = "${local.name_prefix}-bcb-cdi" # lab-data-dev-bcb-cdi
  cdi_prefix = "bcb/sgs/cdi_diario/"          # onde a Lambda pode gravar no bronze
}

# --- Código -----------------------------------------------------------------------
# O Terraform zipa o handler.py; quando o arquivo muda, o hash muda e a Lambda é atualizada.
data "archive_file" "cdi" {
  type        = "zip"
  source_file = "${path.module}/../functions/bcb_cdi/handler.py"
  output_path = "${path.module}/../build/bcb_cdi.zip"
}

# --- Logs -------------------------------------------------------------------------
# Criado antes da função para controlar a retenção (sem ele, a Lambda cria um sem prazo).
resource "aws_cloudwatch_log_group" "cdi" {
  name              = "/aws/lambda/${local.cdi_name}"
  retention_in_days = 14
}

# --- Permissões -------------------------------------------------------------------
# Role que a Lambda assume ao rodar: só escreve logs e grava no prefixo do CDI.
resource "aws_iam_role" "cdi" {
  name = "${local.cdi_name}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "cdi" {
  name = "write-bronze"
  role = aws_iam_role.cdi.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.cdi.arn}:*"
      },
      {
        Sid      = "WriteBronze"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "arn:aws:s3:::${local.bronze_bucket}/${local.cdi_prefix}*"
      },
    ]
  })
}

# --- Função -----------------------------------------------------------------------
resource "aws_lambda_function" "cdi" {
  function_name    = local.cdi_name
  description      = "CDI diário (SGS 12) do Banco Central para o bronze"
  role             = aws_iam_role.cdi.arn
  runtime          = "python3.13"
  handler          = "handler.handler" # arquivo handler.py, função handler
  filename         = data.archive_file.cdi.output_path
  source_code_hash = data.archive_file.cdi.output_base64sha256
  memory_size      = 128
  timeout          = 60

  environment {
    variables = {
      BRONZE_BUCKET = local.bronze_bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.cdi]
}

# --- Agenda -----------------------------------------------------------------------
# Segunda a sexta às 10h (horário de Brasília), com evento vazio: a Lambda busca o dia útil anterior.
resource "aws_scheduler_schedule" "cdi" {
  name                         = local.cdi_name
  description                  = "Dispara a Lambda do CDI nos dias úteis"
  schedule_expression          = "cron(0 10 ? * MON-FRI *)"
  schedule_expression_timezone = "America/Sao_Paulo"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.cdi.arn
    role_arn = aws_iam_role.cdi_scheduler.arn
    input    = jsonencode({})
  }
}

# Role que o Scheduler assume para invocar a Lambda.
resource "aws_iam_role" "cdi_scheduler" {
  name = "${local.cdi_name}-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "cdi_scheduler" {
  name = "invoke-lambda"
  role = aws_iam_role.cdi_scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.cdi.arn
    }]
  })
}
