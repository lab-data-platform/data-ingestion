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

PYTHON_VERSION := 3.13
PACKAGE_DIR    := build/package
ZIP            := build/ingestion.zip
COMPOSE        := docker compose -f local/docker-compose.yml
ifdef LINEAGE
COMPOSE_LINEAGE := --profile lineage
export OPENLINEAGE_URL := http://marquez:5000
export OPENLINEAGE_DISABLED := false
endif

.DEFAULT_GOAL := help

.PHONY: help whoami install lint fmt test contracts build \
        local-up local-test local-down \
        init plan apply destroy run redrive

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

whoami: ## Mostra com qual identidade AWS os comandos vão rodar
	@aws sts get-caller-identity --query Arn --output text

# --- Nível 1: unitário (sem AWS) ---------------------------------------------

install: ## Instala o ambiente Python (uv)
	uv sync

lint: ## ruff (lint + formatação)
	uv run ruff check src tests
	uv run ruff format --check src tests

fmt: ## Formata Python e Terraform
	uv run ruff format src tests
	uv run ruff check --fix src tests
	-terraform fmt -recursive infra

test: ## Testes unitários e de contrato (pytest)
	uv run pytest

contracts: ## Valida os contratos ODCS com o datacontract-cli oficial
	@for f in $$(find assets -name '*.yml' | sort); do \
		echo "== $$f"; uvx --quiet --from 'datacontract-cli==1.2.9' datacontract lint "$$f" | tail -1 || exit 1; \
	done

# --- Build: o zip da Lambda --------------------------------------------------

build: ## Gera build/ingestion.zip (pacote + dependências + contratos + pipelines)
	rm -rf build && mkdir -p $(PACKAGE_DIR)
	uv export --no-dev --no-hashes --no-emit-project --format requirements-txt > build/requirements.txt
	uv pip install -q --target $(PACKAGE_DIR) -r build/requirements.txt \
		--python-version $(PYTHON_VERSION) --python-platform x86_64-manylinux2014 --only-binary :all:
	cp -r src/labdata $(PACKAGE_DIR)/
	cp -r assets $(PACKAGE_DIR)/labdata/assets/_contracts
	cp -r pipelines $(PACKAGE_DIR)/labdata/_pipelines
	find $(PACKAGE_DIR) -name '__pycache__' -prune -exec rm -rf {} +
	cd $(PACKAGE_DIR) && zip -qr ../ingestion.zip .
	@echo "build/ingestion.zip: $$(du -h $(ZIP) | cut -f1)"

# --- Nível 2: integração local (Lambda no container oficial + moto) ----------

local-up: build ## Sobe moto, servidor de fixtures do BCB e a Lambda (LINEAGE=1 para o Marquez)
	$(COMPOSE) $(COMPOSE_LINEAGE) up -d --build --wait
	bash local/seed.sh

local-test: ## Invoca a Lambda no container e confere o resultado no moto
	bash local/verify.sh

local-down: ## Derruba o ambiente local
	$(COMPOSE) --profile lineage down -v

# --- Nível 3: conta real -----------------------------------------------------

init: ## Inicializa o Terraform com o backend remoto
	terraform -chdir=infra init -reconfigure \
		-backend-config="bucket=$(STATE_BUCKET)" \
		-backend-config="key=$(REPO)/$(ENV)/terraform.tfstate" \
		-backend-config="region=$(AWS_REGION)" \
		-backend-config="profile=$(AWS_PROFILE)"

plan: build ## Mostra as mudanças
	terraform -chdir=infra plan -var="environment=$(ENV)" -var="git_commit=$$(git rev-parse --short HEAD)"

apply: build ## Aplica as mudanças
	terraform -chdir=infra apply -var="environment=$(ENV)" -var="git_commit=$$(git rev-parse --short HEAD)"

destroy: ## Destrói o stack
	terraform -chdir=infra destroy -var="environment=$(ENV)"

run: ## Dispara uma execução: make run PIPELINE=bcb/sgs/cdi_diario [DATE=2026-10-29]
	@test -n "$(PIPELINE)" || { echo "informe PIPELINE=<origem>/<níveis...>/<entidade>, ex.: bcb/sgs/cdi_diario"; exit 1; }
	@arn=$$(aws ssm get-parameter --name /$(PLATFORM)/$(ENV)/ingestion/$$(echo $(PIPELINE) | tr / _)_state_machine_arn \
		--query Parameter.Value --output text); \
	input=$$( [ -n "$(DATE)" ] && echo '{"reference_date":"$(DATE)"}' || echo '{}' ); \
	aws stepfunctions start-execution --state-machine-arn $$arn --input "$$input" --query executionArn --output text

redrive: ## Retoma uma execução que falhou: make redrive EXECUTION=<arn>
	@test -n "$(EXECUTION)" || { echo "informe EXECUTION=<arn da execução>"; exit 1; }
	aws stepfunctions redrive-execution --execution-arn $(EXECUTION)
