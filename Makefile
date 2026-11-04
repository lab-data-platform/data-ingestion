SHELL := /bin/bash

REPO        := ingestion
PLATFORM    ?= lab-data
ENV         ?= dev
AWS_PROFILE ?= lab-data
AWS_REGION  ?= us-east-2
export AWS_PROFILE AWS_REGION

# Avaliado só quando usado (=), para não chamar a AWS em todo `make`.
# O $(shell) não herda o `export` do Makefile, por isso o profile vai explícito.
ACCOUNT_ID   = $(shell AWS_PROFILE=$(AWS_PROFILE) aws sts get-caller-identity --query Account --output text)
STATE_BUCKET = $(PLATFORM)-tfstate-$(ACCOUNT_ID)

.DEFAULT_GOAL := help

.PHONY: help whoami test validate init plan apply destroy invoke logs

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

whoami: ## Mostra com qual identidade AWS os comandos vão rodar
	@aws sts get-caller-identity --query Arn --output text

# --- Local (sem AWS) -----------------------------------------------------------

test: ## Testes da Lambda (API e S3 simulados)
	cd functions/bcb_cdi && uv run -q --no-project --python 3.13 --with boto3 python -m unittest -v

validate: ## Valida o Terraform
	terraform -chdir=infra init -backend=false -input=false >/dev/null
	terraform -chdir=infra validate

# --- Conta real ----------------------------------------------------------------

init: ## Inicializa o Terraform com o backend remoto
	terraform -chdir=infra init -reconfigure \
		-backend-config="bucket=$(STATE_BUCKET)" \
		-backend-config="key=$(REPO)/$(ENV)/terraform.tfstate" \
		-backend-config="region=$(AWS_REGION)" \
		-backend-config="profile=$(AWS_PROFILE)"

plan: ## Mostra as mudanças
	terraform -chdir=infra plan -var="environment=$(ENV)"

apply: ## Aplica as mudanças
	terraform -chdir=infra apply -var="environment=$(ENV)"

destroy: ## Destrói os recursos
	terraform -chdir=infra destroy -var="environment=$(ENV)"

invoke: ## Roda a Lambda na AWS: make invoke [DATE=2026-10-30] (sem DATE = dia útil anterior)
	@payload=$$( [ -n "$(DATE)" ] && echo '{"reference_date":"$(DATE)"}' || echo '{}' ); \
	aws lambda invoke --function-name $$(terraform -chdir=infra output -raw cdi_function_name) \
		--cli-binary-format raw-in-base64-out --payload "$$payload" /dev/stdout

logs: ## Mostra os logs da Lambda dos últimos 30 minutos
	aws logs tail $$(terraform -chdir=infra output -raw cdi_log_group) --since 30m
