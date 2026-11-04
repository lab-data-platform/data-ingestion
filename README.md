# data-ingestion

Ingestão da plataforma `lab-data`: traz dados das fontes externas para a camada **bronze** do lakehouse.

## Status

📘 **Exercício de Lambda, concluído em 2026-11-03.** A rotina do CDI foi aplicada, executada (gravou `reference_date=2026-10-30`) e destruída.

**Este repositório não é a ferramenta de ingestão da plataforma.** Lambda com uma agenda por rotina não escala para centenas de pipelines (cada rotina vira ~7 recursos e um `terraform apply`). A ingestão da plataforma vai para o **Airflow**, num repositório próprio.

A primeira versão (framework próprio, contratos ODCS e Step Functions) foi descartada pelo mesmo motivo e continua no histórico do Git (commit `138559e`).

## Como funciona

```text
EventBridge Scheduler (seg a sex, 10h)
        │  evento {}
        ▼
Lambda lab-data-dev-bcb-cdi ── GET api.bcb.gov.br (série 12, de D até D+1)
        │
        ▼
s3://lab-data-dev-bronze-<account_id>/bcb/sgs/cdi_diario/reference_date=AAAA-MM-DD/data.jsonl
```

- **Evento vazio** (agenda): busca o dia útil anterior. **`{"reference_date": "2026-10-30"}`**: busca esse dia (reprocessamento).
- **Sem dado** (fim de semana, feriado): a API responde 404, a Lambda devolve `no_data` e não grava nada.
- **Rodar de novo o mesmo dia** sobrescreve o mesmo arquivo: não duplica.
- O arquivo é JSON Lines (um objeto por linha), o formato que o Athena lê.

## Estrutura

```text
functions/bcb_cdi/
├── handler.py        # a Lambda: um arquivo, sem dependências (urllib + boto3 do runtime)
└── test_handler.py   # testes com a API e o S3 simulados
infra/
├── main.tf           # provider e o que vem dos outros repositórios (SSM)
├── bcb_cdi.tf        # zip, log group, roles, função e agenda
└── ...
```

## Recursos na AWS

Nenhum no ar: o exercício foi destruído com `make destroy`. O arquivo gravado continua no bronze. Para refazer: `make apply`. **Região:** `us-east-2` (Ohio).

| Serviço AWS | Recurso | Para que serve | Custo | Código | Onde ver no console |
|---|---|---|---|---|---|
| **AWS Lambda** | `lab-data-dev-bcb-cdi` | Busca o CDI e grava no bronze | grátis (1 milhão de invocações/mês) | `infra/bcb_cdi.tf` | Lambda → Functions |
| **Amazon EventBridge Scheduler** | `lab-data-dev-bcb-cdi` | Dispara a Lambda de segunda a sexta, 10h | grátis (14 milhões/mês) | `infra/bcb_cdi.tf` | EventBridge → Schedules |
| **AWS IAM** | Roles `lab-data-dev-bcb-cdi-lambda` e `-scheduler` | Permissão mínima da Lambda e da agenda | grátis | `infra/bcb_cdi.tf` | IAM → Roles |
| **Amazon CloudWatch** | Log group `/aws/lambda/lab-data-dev-bcb-cdi` | Logs das execuções, 14 dias | centavos | `infra/bcb_cdi.tf` | CloudWatch → Log groups |

## Depende de

| Repositório | O que usa (SSM) |
|---|---|
| `data-foundation` | `name_prefix` e o bucket de state |
| `data-lakehouse` | `bronze_bucket` |

## Uso

```bash
make help                    # lista os comandos
make test                    # testes da Lambda, sem AWS
make validate                # valida o Terraform
make init && make plan       # mostra o que vai ser criado
make apply                   # cria na AWS
make invoke DATE=2026-10-30  # roda a Lambda na AWS para um dia
make invoke                  # roda para o dia útil anterior
make logs                    # logs dos últimos 30 minutos
```

## Qualidade

| O quê | Como |
|---|---|
| pre-commit | `pre-commit install` (hooks de higiene e gitleaks) |
| CI | GitHub Actions roda o pre-commit em todo push e PR |
