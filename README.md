# data-ingestion

Ingestão das fontes de dados para a camada **bronze** da plataforma `lab-data`, em arquitetura **serverless**: AWS Lambda para extrair, AWS Step Functions para orquestrar cada pipeline e Amazon EventBridge para agendar e avisar quando um asset fica pronto. Visão geral em [data-platform](https://github.com/lab-data-platform/data-platform).

> ⏳ **Camada 4 em construção.** Primeira pipeline: **CDI diário** (`bronze.bcb.sgs.cdi_diario`), pronta e testada localmente nos níveis 1 e 2. Falta a infraestrutura na conta (Terraform). Escopo no [ROADMAP](https://github.com/lab-data-platform/data-platform/blob/main/ROADMAP.md#camada-4--ingestão).

---

## Como funciona

```
 EventBridge Scheduler ──► Step Functions (1 state machine por pipeline)
 (seg a sex, 10h BRT)      ┌───────────────────────────────┐     ┌─────────────────────────────┐
                           │ Executar (Lambda)             │     │ status = ok                 │
                           │  extrair → validar → gravar   │────►│  → publica AssetUpdated     │
                           │  + OpenLineage                │     │    (EventBridge, nativo)    │
                           └──────────────┬────────────────┘     │ status = no_data → fim      │
                              retry 3x    │                      │ status = quarantined → alerta
                              falhou de   ▼                      └─────────────────────────────┘
                              vez ──► alerta (SNS lab-data-dev-alerts)

 Lambda grava em:  S3 bronze  bcb/sgs/cdi_diario/reference_date=<D>/{data.json, _manifest.json}
              ou:  S3 bronze  _quarantine/bcb/sgs/cdi_diario/reference_date=<D>/{data.json, _reason.json}
```

- **Uma Lambda faz o trabalho, a state machine orquestra.** A Lambda extrai, valida pelo contrato, grava no bronze (ou na quarentena) e emite a linhagem; a state machine tenta de novo, decide pelo `status`, publica o `AssetUpdated` e alerta. A tabela bronze usa *partition projection*: o Glue descobre as partições pelo caminho, sem passo de registro.
- **O código mora neste repositório.** O `make build` gera um `.zip` com o pacote, os contratos e as pipelines; o `make apply` (Terraform) envia o zip para as Lambdas. Ninguém edita código no console: o próximo `apply` sobrescreveria a mudança. Cada Lambda leva a tag `GitCommit`.
- **Uma pipeline = um YAML + um contrato.** O Terraform lê `pipelines/**/*.yml` e cria, para cada arquivo, a Lambda, a state machine, a agenda, a role e a tabela bronze. Um extrator atende um sistema inteiro: uma série nova do SGS não exige código novo.
- **Assets, linhagem e eventos** seguem o [padrão de assets](https://github.com/lab-data-platform/data-platform/blob/main/docs/assets.md) da plataforma: ID em caminho, contrato **ODCS**, **OpenLineage** em toda execução e `AssetUpdated` quando o asset fica pronto.

---

## Estrutura

O pacote `labdata` tem três pilares, com nomes que não se confundem:

| Pilar | Responde | Import |
|---|---|---|
| `assets/` | **O que** é cada dado (constantes lidas dos contratos) | `from labdata.assets.bronze.bcb import sgs` |
| `sdk/` | **Como** a ingestão funciona (framework comum) | `from labdata.sdk.core import Extractor` |
| `extractors/` | **Como** buscar cada origem (classes `Extractor`) | `from labdata.extractors.bcb import Sgs` |

A camada de asset `source` (em `assets/source/`) é o **dado** de origem; o `extractors/` é o **código** que o busca.

| Separação | Pasta | Equivalente num projeto Airflow |
|---|---|---|
| **Framework** | `src/labdata/sdk/` | `plugins/<empresa>/sdk/`, hooks |
| **Governança** (contratos, qualidade, linhagem, classificação) | `src/labdata/sdk/governance/` | `validators/`, data contracts |
| **Extração** (o código de cada origem) | `src/labdata/extractors/<origem>/<sistema>.py` | `dags/extract/<fonte>/` |
| **Registro de assets** (contrato ODCS) | `assets/<camada>/<origem>/<níveis...>/<entidade>.yml` | `plugins/<empresa>/assets/<camada>/<fonte>` |
| **Lib de assets** | `src/labdata/assets/<camada>/<origem>/<níveis...>.py` | Constantes de asset importadas pelas DAGs |
| **Pipelines** (o que roda, como e quando) | `pipelines/<origem>/<níveis...>/<entidade>.yml` | Arquivos de DAG |

```
data-ingestion/
│
├── src/labdata/                                # PACOTE PYTHON: vira o .zip das Lambdas (namespace: sem __init__.py)
│   ├── assets/                                 # LIB DE ASSETS (namespace: sem __init__.py)
│   │   ├── source/bcb/sgs.py                   #   labdata.assets.source.bcb.sgs.cdi_diario
│   │   └── bronze/bcb/sgs.py                   #   labdata.assets.bronze.bcb.sgs.cdi_diario (id, s3_prefix, table, uri)
│   │
│   ├── sdk/                                    # FRAMEWORK da ingestão
│   │   ├── core/                               #   abstrações e modelos, sem nenhuma dependência da AWS
│   │   │   ├── extractor.py                    #     classe base Extractor: o "molde" de toda origem
│   │   │   ├── models.py                       #     RawFile, ExtractRequest, RunContext, ExtractResult
│   │   │   ├── ports.py                        #     interfaces que os adaptadores implementam (ObjectStore, HttpClient)
│   │   │   └── errors.py                       #     SourceUnavailable, NoData, ValidationFailed...
│   │   ├── adapters/                           #   integrações com o mundo externo (o papel dos hooks)
│   │   │   ├── aws/s3.py                       #     ObjectStore sobre o S3 (ou o moto, no ambiente local)
│   │   │   └── http/client.py                  #     cliente HTTP com timeout e retry
│   │   ├── layers/
│   │   │   └── bronze/                         #   camada bronze (outra camada entra como pasta irmã)
│   │   │       ├── layout.py                   #     caminhos: <caminho do asset>/reference_date=<AAAA-MM-DD>/
│   │   │       └── writer.py                   #     grava o arquivo como veio + manifesto, substituindo a partição
│   │   ├── governance/                         #   GOVERNANÇA: as regras sobre o dado, num lugar só
│   │   │   ├── contracts/
│   │   │   │   ├── assets.py                   #     carrega os contratos ODCS e deriva os nomes físicos do ID
│   │   │   │   └── events.py                   #     monta o detail do AssetUpdated
│   │   │   ├── quality/
│   │   │   │   ├── rules.py                    #     regras do contrato (required, rowCount...)
│   │   │   │   ├── validator.py                #     aplica as regras aos arquivos extraídos
│   │   │   │   └── quarantine.py               #     grava em _quarantine/ com o motivo
│   │   │   ├── lineage/
│   │   │   │   ├── manifest.py                 #     colunas técnicas (_ingested_at, _source, _run_id, _partition...)
│   │   │   │   └── openlineage.py              #     eventos OpenLineage (START, COMPLETE, FAIL)
│   │   │   └── classification.py               #     public, internal, confidential, personal
│   │   └── runtime/                            #   como o código roda: hoje Lambda, amanhã Airflow
│   │       ├── lambda_handler.py               #     handler genérico: o mesmo para toda pipeline
│   │       ├── pipeline.py                     #     o fluxo: extrair → validar → gravar/quarentena → linhagem
│   │       ├── config.py                       #     lê o ambiente e o arquivo da pipeline
│   │       ├── dates.py                        #     data de referência (dia útil anterior)
│   │       └── logging.py                      #     log estruturado em JSON, com o run_id
│   │
│   └── extractors/                             # EXTRAÇÃO: um módulo por sistema de cada origem
│       └── bcb/
│           ├── client.py                       #   o que é comum ao BCB (URL, formato de data)
│           └── sgs.py                          #   class Sgs(Extractor): qualquer série do SGS
│
├── assets/                                     # REGISTRO DE ASSETS: um contrato ODCS v3.2.0 por asset
│   ├── source/bcb/sgs/cdi_diario.yml           #   source.bcb.sgs.cdi_diario (a série 12 na API do BCB)
│   └── bronze/bcb/sgs/cdi_diario.yml           #   bronze.bcb.sgs.cdi_diario
│
├── pipelines/                                  # PIPELINES: 1 arquivo = 1 pipeline = o caminho do asset
│   └── bcb/sgs/cdi_diario.yml                  #   extrator + série, agenda, recursos, retry
│
├── infra/                                      # TERRAFORM (próximo passo)
│   ├── modules/pipeline/                       #   Lambda, state machine, agenda, roles, tabela bronze
│   ├── pipelines.tf                            #   lê pipelines/**/*.yml e cria um módulo por arquivo
│   └── tests/
│
├── tests/
│   ├── unit/                                   #   nível 1: espelha o src/
│   │   ├── sdk/{core,adapters,layers,governance,runtime}/
│   │   └── extractors/bcb/test_sgs.py
│   ├── contracts/                              #   assets/ e pipelines/ válidos e coerentes entre si
│   ├── integration/                            #   nível 2 (via make local-test)
│   └── fixtures/bcb/sgs/cdi_diario/            #   respostas reais da API, gravadas
│
├── local/                                      # AMBIENTE LOCAL (nível 2)
│   ├── docker-compose.yml                      #   moto + servidor de fixtures do BCB + Lambda no container oficial + Marquez
│   ├── Dockerfile                              #   public.ecr.aws/lambda/python:3.13 com o build/
│   ├── bcb-stub/server.py                      #   faz o papel da API do BCB, a partir das fixtures
│   ├── seed.sh                                 #   cria o bucket do bronze no moto
│   └── verify.sh                               #   invoca a Lambda e confere o resultado no moto
│
├── schemas/
│   ├── pipeline.schema.json                    # formato dos arquivos de pipelines/
│   └── platform/                               # cópia fixada dos schemas do data-platform (ORIGEM diz a versão)
│
├── docs/runbooks/                              # procedimentos por origem (próximo passo)
├── build/                                      # gerado pelo make build (fora do Git)
├── pyproject.toml · uv.lock                    # dependências (uv), pytest e ruff
├── Makefile · CLAUDE.md · README.md
└── .github/                                    # CI e Dependabot
```

### Regras da estrutura

1. **O `sdk/` não conhece o `extractors/`, e o `extractors/` não reimplementa o `sdk/`.** Uma origem nova só implementa o `extract()`; validar, gravar, mandar para a quarentena, logar e emitir linhagem vêm do `sdk/`.
2. **Só o `sdk/adapters/` fala com o mundo externo** (AWS, HTTP). `core/`, `layers/` e `governance/` não importam `boto3`: são testados sem rede, e o mesmo código pode rodar no Airflow trocando só o `runtime/` (portas e adaptadores).
3. **Asset ≠ pipeline.** O asset diz *o que* é o dado (contrato); a pipeline diz *como e quando* ele é produzido.
4. **A hierarquia é sempre o caminho do asset, `<origem>/<níveis...>/<entidade>`**, sem domínio, em `assets/`, `pipelines/`, `src/labdata/assets/`, `tests/fixtures/` e `docs/runbooks/`. O `extractors/` para no sistema (`bcb/sgs.py`), porque um extrator atende o sistema inteiro.
5. **O domínio não é pasta nem ID**: fica no campo `domain` do contrato e na tag `Domain`, e pode ser corrigido sem mover nada ([ADR-0021](https://github.com/lab-data-platform/data-platform/blob/main/docs/decisoes/0021-identidade-de-asset-como-caminho.md)).
6. **Toda regra sobre o dado mora em `sdk/governance/`**: contrato, qualidade, quarentena, linhagem e classificação.
7. **`layers/` segue a arquitetura medalhão**: cada camada é uma pasta, mesmo que hoje só exista o `bronze/`.
8. **Pasta só existe quando tem conteúdo.**
9. **Os nomes principais são reexportados no `__init__.py`** de cada pacote. Exceção: `labdata/` e `labdata/assets/` **não têm `__init__.py`** (namespace packages compartilhados com outros repositórios).
10. **Nenhum ID ou nome físico escrito à mão.** Caminho no S3, tabela, URI e identidade OpenLineage vêm sempre do asset (`sgs.cdi_diario.s3_prefix`, `sgs.cdi_diario.table`...).

### Como fica adicionar uma pipeline

**Outra série de um sistema que já existe** (ex.: a Selic diária, série 11 do SGS), sem código novo:

| # | Arquivo | O quê |
|---|---|---|
| 1 | `assets/source/bcb/sgs/selic_diaria.yml` | Contrato da fonte |
| 2 | `assets/bronze/bcb/sgs/selic_diaria.yml` | Contrato do bronze |
| 3 | `src/labdata/assets/{source,bronze}/bcb/sgs.py` | Uma linha em cada: `selic_diaria = asset("...")` |
| 4 | `pipelines/bcb/sgs/selic_diaria.yml` | `class: labdata.extractors.bcb.sgs:Sgs`, `series: 11`, agenda |

**Uma origem ou sistema novo** (ex.: o informe diário de fundos da CVM): além dos passos acima (`assets/.../cvm/fi/doc/inf_diario.yml`, `pipelines/cvm/fi/doc/inf_diario.yml`), entram o extrator `src/labdata/extractors/cvm/fi.py` com o `extract()`, o teste `tests/unit/extractors/cvm/test_fi.py` com fixtures gravadas e o runbook.

Nenhum arquivo do `sdk/` nem do `infra/` muda: o CI valida os contratos e as pipelines, e o `make apply` cria os recursos.

---

## Como o dado fica salvo

O código fica no repositório; o **dado** fica no bucket do bronze (contrato `/lab-data/<env>/lakehouse/bronze_bucket`):

```
s3://lab-data-dev-bronze-<account_id>/
├── bcb/sgs/cdi_diario/                                    ← asset bronze.bcb.sgs.cdi_diario
│   └── reference_date=2026-10-29/                         ← uma partição por dia de referência
│       ├── data.json                                      ← a observação do dia, como veio da API
│       └── _manifest.json                                 ← colunas técnicas, janela pedida, estatísticas e hash
└── _quarantine/bcb/sgs/cdi_diario/reference_date=.../     ← o que falhou na validação, com _reason.json
```

- **Reexecutar o mesmo dia substitui** a partição inteira, e nunca duplica ([governança](https://github.com/lab-data-platform/data-platform/blob/main/docs/governanca.md#5-idempotência-e-reprocessamento)).
- **Só o dado do dia.** A API do SGS recusa janela de um dia só, então o extrator pede `D → D+1` e grava só a observação de `D`.
- **Sem dado (fim de semana, feriado):** a API responde 404, a execução termina com `status = no_data`, sem gravar e sem evento.
- A tabela `lab_data_dev_bronze.bcb_sgs_cdi_diario` aponta para `bcb/sgs/cdi_diario/`. Os dois nomes são derivados do ID ([nomes físicos](https://github.com/lab-data-platform/data-platform/blob/main/docs/assets.md#2-nomes-físicos-derivados)).

---

## Recursos na AWS (previstos)

Nada foi criado ainda. **Uma linha por pipeline** em cada recurso. **Região:** `us-east-2` (Ohio).

| Serviço AWS | Recurso | Para que serve | Região | Custo | Código | Onde ver no console |
|---|---|---|---|---|---|---|
| **AWS Lambda** | `lab-data-dev-ingest-<caminho>` (ex.: `...-bcb-sgs-cdi-diario`) | Extrair, validar, gravar e emitir linhagem | `us-east-2` | grátis no volume do lab | `infra/modules/pipeline/` | Lambda → Functions |
| **AWS Step Functions** | State machine `lab-data-dev-ingest-<caminho>` | Retry, decisão pelo status, AssetUpdated e alerta | `us-east-2` | grátis (4 mil transições/mês) | `infra/modules/pipeline/` | Step Functions → State machines |
| **Amazon EventBridge Scheduler** | Agenda por pipeline (seg a sex, 10h BRT) | Dispara a state machine | `us-east-2` | grátis | `infra/modules/pipeline/` | EventBridge → Schedules |
| **AWS IAM** | Roles da Lambda, da state machine e da agenda | Permissão mínima por pipeline | global | grátis | `infra/modules/pipeline/` | IAM → Roles |
| **AWS Glue** (Data Catalog) | Tabela bronze por asset, com *partition projection* | Torna o dado consultável pelo Athena | `us-east-2` | grátis | `infra/modules/pipeline/` | Glue → Tables |
| **Amazon CloudWatch** | Log group por Lambda | Logs JSON das execuções, retenção curta | `us-east-2` | centavos | `infra/modules/pipeline/` | CloudWatch → Log groups |
| **AWS Systems Manager** | Parâmetros em `/lab-data/dev/ingestion/` | ARN de cada state machine | `us-east-2` | grátis | `infra/contract.tf` | Parameter Store |

## Depende de

| Repositório | O que usa |
|---|---|
| `data-foundation` | `alerts_topic_arn` (alertas) e `assets_event_bus_name`/`_arn` (eventos) |
| `data-lakehouse` | `bronze_bucket`, `glue_database_bronze` e `athena_workgroup` |
| `data-platform` | Padrão de assets e schemas de validação, numa cópia fixada em `schemas/platform/` |

---

## Uso

```bash
make help            # lista os comandos
make install         # ambiente Python (uv)

# Nível 1: sem AWS
make test            # pytest: unitários e contratos
make lint            # ruff
make contracts       # datacontract lint (ODCS oficial) em todos os contratos

# Nível 2: sem AWS, no runtime real da Lambda
make local-up        # build + moto + servidor de fixtures + Lambda (LINEAGE=1 para o Marquez)
make local-test      # invoca a Lambda e confere o resultado no moto
make local-down

# Nível 3: conta real (depois do Terraform)
make build · make init · make plan · make apply
make run PIPELINE=bcb/sgs/cdi_diario [DATE=2026-10-29]   # dispara uma execução
make redrive EXECUTION=<arn>                             # retoma uma execução que falhou
```

## Testes

| Nível | Onde | O que cobre |
|---|---|---|
| 1. Unitário | `tests/unit/`, `tests/contracts/` | Regras do `sdk/` sem rede; extrator do SGS com respostas reais gravadas; IDs de qualquer profundidade; contratos e pipelines coerentes (59 testes) |
| 1. Contratos | `make contracts` | Formato ODCS v3.2.0 pela ferramenta oficial (`datacontract lint`) |
| 2. Integração local | `make local-up` + `make local-test` | A Lambda no **container oficial da AWS**, contra o **moto** e um servidor de fixtures do BCB: dia útil, reexecução sem duplicar, fim de semana sem dado (8 verificações); linhagem no **Marquez** com `LINEAGE=1` |
| 3. Real | `make run` | Execução na conta, com o fluxo visível no console do Step Functions |

## Qualidade

| Verificação | Onde roda | O que cobre |
|---|---|---|
| Pré-commit | Na sua máquina, a cada `git commit` | Segredos (gitleaks, credenciais AWS, chaves privadas), YAML, espaços e fim de arquivo, commit direto na `main`; previsto: ruff e `datacontract lint` |
| CI | GitHub Actions ([ci.yml](.github/workflows/ci.yml)), em todo PR e push na `main` e na `develop` | O mesmo pre-commit; previsto: jobs de Python (ruff + pytest + contratos), Terraform e integração local |

```bash
pre-commit install            # uma vez por clone: ativa os hooks
pre-commit run --all-files    # roda todos os hooks manualmente
```
