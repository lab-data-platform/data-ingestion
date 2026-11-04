provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  # Tags aplicadas automaticamente em todo recurso (convenções no data-platform).
  default_tags {
    tags = {
      Platform    = var.platform
      Environment = var.environment
      Component   = "ingestion"
      ManagedBy   = "terraform"
      Repository  = "data-ingestion"
    }
  }
}

# O que vem dos outros repositórios, pelo contrato no SSM (data-platform/docs/contratos.md).
data "aws_ssm_parameter" "name_prefix" {
  name = "/${var.platform}/${var.environment}/foundation/name_prefix"
}

data "aws_ssm_parameter" "bronze_bucket" {
  name = "/${var.platform}/${var.environment}/lakehouse/bronze_bucket"
}

locals {
  name_prefix   = data.aws_ssm_parameter.name_prefix.insecure_value # lab-data-dev
  bronze_bucket = data.aws_ssm_parameter.bronze_bucket.insecure_value
}
