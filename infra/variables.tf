variable "platform" {
  description = "Nome da plataforma, usado nos caminhos do contrato SSM."
  type        = string
  default     = "lab-data"
}

variable "environment" {
  description = "Ambiente da plataforma."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Região AWS da plataforma (única liberada no plano gratuito, ADR-0013)."
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "Profile do AWS CLI."
  type        = string
  default     = "lab-data"
}
