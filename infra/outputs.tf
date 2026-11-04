output "cdi_function_name" {
  description = "Nome da Lambda do CDI (usado no make invoke)."
  value       = aws_lambda_function.cdi.function_name
}

output "cdi_log_group" {
  description = "Log group da Lambda do CDI (usado no make logs)."
  value       = aws_cloudwatch_log_group.cdi.name
}
