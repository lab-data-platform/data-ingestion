terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    # Gera o zip da Lambda a partir do handler.py.
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }

  # Configuração parcial: bucket, key e região são passados no `make init`.
  # O bucket de state é criado pelo data-foundation/bootstrap.
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
