# data-ingestion

Ingestão das fontes de dados para a camada bronze da plataforma `lab-data`. Visão geral em [data-platform](../data-platform/README.md).

> ⬜ **Planejado.** Este repositório é construído na **camada 4**. Escopo e critério de pronto em [ROADMAP.md](../data-platform/ROADMAP.md#camada-4--ingestão).

## Escopo

| Entrega | Detalhe |
|---|---|
| Definição das fontes | É aqui que se estuda o dado: API, formato, volume, frequência, histórico |
| Módulo Terraform reutilizável por fonte | Lambda, role IAM, state machine e tabela bronze; uma fonte nova é uma instância nova do módulo |
| State machine por fonte (Step Functions) | Extrair → validar → registrar, com retry e alerta de falha |
| Código de extração | Lambdas em Python, organizadas por domínio (`src/financeiro/<fonte>/`) |
| Cargas | Histórica (backfill) e incremental, idempotentes |

## Recursos na AWS (previstos)

Nada foi criado ainda. Previsão para a camada 4, a confirmar no escopo: **uma linha por fonte** para cada recurso. **Região:** `us-east-2` (Ohio).

| Serviço AWS | Recurso | Para que serve | Região | Custo | Código | Onde ver no console |
|---|---|---|---|---|---|---|
| **AWS Lambda** | Função `lab-data-dev-ingest-<fonte>` | Extrai os dados da fonte e grava no bronze | `us-east-2` | grátis no volume do lab | `infra/modules/source/` | Lambda → Functions |
| **AWS Step Functions** | State machine `lab-data-dev-ingest-<fonte>` | Extrair → validar → registrar, com retry e alerta de falha | `us-east-2` | centavos | `infra/modules/source/` | Step Functions → State machines |
| **AWS IAM** | Role por fonte | Permissão mínima para a Lambda e a state machine | global | grátis | `infra/modules/source/` | IAM → Roles |
| **AWS Glue** (Data Catalog) | Tabela bronze por fonte | Torna o dado bruto consultável pelo Athena | `us-east-2` | grátis | `infra/modules/source/` | Glue → Tables |
| **Amazon CloudWatch** | Log groups das Lambdas e state machines | Logs de execução, com retenção curta | `us-east-2` | centavos | `infra/modules/source/` | CloudWatch → Log groups |
| **Amazon EventBridge** | Agenda provisória por fonte | Dispara a ingestão até o Airflow existir | `us-east-2` | grátis | `infra/` | EventBridge → Schedules |

## Estrutura prevista

```
data-ingestion/
├── infra/
│   ├── modules/source/   # módulo reutilizável: uma instância por fonte
│   └── tests/
├── src/financeiro/       # código das Lambdas por fonte
├── tests/                # pytest com moto
├── local/                # moto (Lambda, S3, Step Functions) em Docker
├── Makefile
├── CLAUDE.md
└── README.md
```

## Depende de

- `data-foundation`: `/lab-data/<env>/foundation/alerts_topic_arn`
- `data-lakehouse`: `/lab-data/<env>/lakehouse/bronze_bucket` e `glue_database_bronze`
