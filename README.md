# data-ingestion

Ingestão das fontes de dados para a camada **bronze** da plataforma `lab-data`, em arquitetura **serverless**: AWS Lambda para extrair, AWS Step Functions para orquestrar cada pipeline e Amazon EventBridge para agendar e avisar quando um asset fica pronto. Visão geral em [data-platform](https://github.com/lab-data-platform/data-platform).

> ✅ **Estrutura aprovada** em 2026-11-02. Este README descreve a organização do repositório; o código é criado a partir dela na **camada 4** ([ROADMAP](https://github.com/lab-data-platform/data-platform/blob/main/ROADMAP.md#camada-4--ingestão)).

---

## Como funciona

```
 EventBridge Scheduler ──► Step Functions (1 state machine por pipeline) ───────────────────────────────┐
  (agenda diária)          ┌──────────────┐   ┌──────────┐   ┌───────────┐   ┌─────────────────────┐  │
                           │ Extrair      │──►│ Validar  │──►│ Registrar │──►│ Publicar            │  │
                           │ (Lambda)     │   │ (Lambda) │   │ partição  │   │ AssetUpdated        │  │
                           └──────┬───────┘   └────┬─────┘   │ (Glue)    │   │ (EventBridge)       │  │
                                  │                │         └───────────┘   └─────────────────────┘  │
                                  ▼                ▼ falhou                                             │
                        S3 bronze (arquivo     S3 _quarantine/  ──► alerta (SNS lab-data-dev-alerts) ◄──┘
                        original + manifesto)                       em qualquer falha definitiva
```

- **O código mora neste repositório.** O `make build` gera um `.zip` com o pacote Python, e o `make apply` (Terraform) envia esse zip para as Lambdas. Ninguém edita código no console da AWS: o próximo `apply` sobrescreveria a mudança. Cada Lambda leva a tag `GitCommit` com o commit de origem.
- **Uma pipeline = um YAML + uma classe Python.** O Terraform lê `pipelines/**/*.yml` e cria, para cada arquivo, a Lambda, a state machine, a agenda, a role IAM e a tabela bronze.
- **Assets, linhagem e eventos:** cada pipeline produz um asset com contrato **ODCS** em `assets/`, segue o [padrão de assets](https://github.com/lab-data-platform/data-platform/blob/main/docs/assets.md) da plataforma, emite **OpenLineage** em toda execução e publica `AssetUpdated` quando o asset fica pronto ([eventos](https://github.com/lab-data-platform/data-platform/blob/main/docs/eventos.md)).

---

## Estrutura

A organização segue estas separações, como num projeto Airflow com `plugins/` e `dags/`:

| Separação | Pasta | Equivalente num projeto Airflow |
|---|---|---|
| **Framework** (o que é comum a toda ingestão) | `src/labdata/sdk/` | `plugins/<empresa>/sdk/`, hooks, validators |
| **Governança** (regras sobre o dado: contratos, qualidade, linhagem, classificação) | `src/labdata/sdk/governance/` | `validators/`, registro de assets, data contracts |
| **Extração** (o código específico de cada fonte) | `src/labdata/extract/<domínio>/<fonte>/` | `dags/extract/<fonte>/` |
| **Registro de assets** (o que é cada dado: contrato ODCS) | `assets/<camada>/<domínio>/<fonte>/<entidade>.yml` | `plugins/<empresa>/assets/<camada>/<fonte>` |
| **Lib de assets** (os contratos como constantes importáveis) | `src/labdata/assets/<camada>/<domínio>/<fonte>.py` | As constantes de asset importadas pelas DAGs |
| **Pipelines** (o que roda, como e quando) | `pipelines/<domínio>/<fonte>/<entidade>.yml` | Arquivos de DAG |

```
data-ingestion/
│
├── src/
│   └── labdata/                                # PACOTE PYTHON: vira o .zip das Lambdas (namespace: sem __init__.py)
│       │
│       ├── assets/                             # LIB DE ASSETS: lê os contratos de assets/ (namespace: sem __init__.py)
│       │   ├── source/financeiro/
│       │   │   └── bcb.py                      #   labdata.assets.source.financeiro.bcb.sgs
│       │   └── bronze/financeiro/
│       │       └── bcb.py                      #   labdata.assets.bronze.financeiro.bcb.sgs (id, s3_prefix, table, uri)
│       │
│       ├── sdk/                                # FRAMEWORK da ingestão
│       │   ├── core/                           #   abstrações e modelos, sem nenhuma dependência da AWS
│       │   │   ├── extractor.py                #     classe base Extractor: o "molde" de toda fonte
│       │   │   ├── models.py                   #     RawFile, ExtractRequest, RunContext, ExtractResult
│       │   │   └── errors.py                   #     SourceUnavailable, ValidationFailed...
│       │   │
│       │   ├── adapters/                       #   integrações com o mundo externo (o papel dos hooks)
│       │   │   ├── aws/
│       │   │   │   ├── s3.py                   #     ler e gravar objetos
│       │   │   │   ├── ssm.py                  #     ler os contratos da plataforma
│       │   │   │   └── eventbridge.py          #     publicar eventos
│       │   │   └── http/
│       │   │       └── client.py               #     cliente HTTP com timeout, retry e user-agent
│       │   │
│       │   ├── layers/                         #   camadas de dado (arquitetura medalhão)
│       │   │   └── bronze/                     #     hoje, só o bronze; outra camada entra como pasta irmã
│       │   │       ├── layout.py               #       caminhos: <domínio>/<fonte>/<entidade>/<partições>/ingestion_date=<data>/
│       │   │       └── writer.py               #       grava o arquivo original + manifesto
│       │   │
│       │   ├── governance/                     #   GOVERNANÇA: as regras sobre o dado, num lugar só
│       │   │   ├── contracts/                  #     contratos
│       │   │   │   ├── assets.py               #       carrega os contratos ODCS e deriva os nomes físicos do ID
│       │   │   │   └── events.py               #       modelo do evento AssetUpdated
│       │   │   ├── quality/                    #     qualidade (o papel dos validators)
│       │   │   │   ├── rules.py                #       regras do quality dos contratos ODCS (rowCount, required...)
│       │   │   │   ├── validator.py            #       aplica as regras a um arquivo
│       │   │   │   └── quarantine.py           #       grava em _quarantine/ com o motivo
│       │   │   ├── lineage/                    #     linhagem
│       │   │   │   ├── manifest.py             #       colunas técnicas (_ingested_at, _source, _run_id...)
│       │   │   │   └── openlineage.py          #       emite os eventos OpenLineage (START, COMPLETE, FAIL)
│       │   │   └── classification.py           #     classificações (publico, interno, confidencial, pessoal)
│       │   │
│       │   └── runtime/                        #   como o código roda: hoje Lambda, amanhã Airflow
│       │       ├── lambda_handler.py           #     transforma um Extractor num handler de Lambda
│       │       ├── config.py                   #     configuração vinda do ambiente (região, endpoints)
│       │       └── logging.py                  #     log estruturado em JSON, com o run_id
│       │
│       └── extract/                            # EXTRAÇÃO: o código de cada fonte, domínio → fonte → entidade
│           └── financeiro/
│               └── bcb/
│                   ├── client.py               #   o que é comum ao BCB (URL base, janelas de consulta)
│                   └── sgs.py                  #   class Sgs(Extractor): só o método extract()
│
├── assets/                                 # REGISTRO DE ASSETS: um contrato ODCS v3.2.0 por asset
│   ├── source/financeiro/bcb/
│   │   └── sgs.yml                         #   source.financeiro.bcb.sgs (fonte externa: API, arquivo, banco...)
│   └── bronze/financeiro/bcb/
│       └── sgs.yml                         #   bronze.financeiro.bcb.sgs: schema, dono, qualidade, frescor e as
│                                           #   extensões da plataforma (classificação, criticidade, depende_de...)
│
├── pipelines/                              # PIPELINES: 1 arquivo = 1 pipeline
│   └── financeiro/bcb/
│       └── sgs.yml                         #   asset produzido (ID), handler, agenda, memória, timeout,
│                                           #   input padrão (ex.: séries) e janela da carga histórica
│
├── infra/                                  # TERRAFORM
│   ├── modules/
│   │   └── pipeline/                       #   tudo o que uma pipeline precisa na AWS, um arquivo por recurso
│   │       ├── lambda.tf                   #     funções e log groups
│   │       ├── state_machine.tf            #     state machine
│   │       ├── state-machine.asl.json      #     fluxo: extrair → validar → registrar → publicar
│   │       ├── schedule.tf                 #     agenda do EventBridge Scheduler
│   │       ├── catalog.tf                  #     tabela bronze no Glue
│   │       ├── iam.tf                      #     roles com permissão mínima
│   │       ├── variables.tf
│   │       └── outputs.tf
│   ├── pipelines.tf                        #   lê pipelines/**/*.yml e cria um módulo por arquivo
│   ├── build.tf                            #   referência ao .zip gerado pelo make build
│   ├── main.tf                             #   provider e leitura dos contratos (foundation e lakehouse)
│   ├── contract.tf                         #   contrato publicado (ARN de cada state machine)
│   ├── variables.tf · outputs.tf · versions.tf
│   └── tests/                              #   terraform test com provider simulado
│
├── tests/                                  # TESTES PYTHON
│   ├── unit/                               #   nível 1: espelha o src/
│   │   ├── sdk/
│   │   │   └── core/ · adapters/ · layers/ · governance/ · runtime/
│   │   └── extract/financeiro/bcb/
│   │       └── test_sgs.py
│   ├── integration/                        #   nível 2: Lambda no container oficial + moto
│   ├── contracts/                          #   valida assets/ (datacontract lint + extensões) e pipelines/
│   └── fixtures/financeiro/bcb/sgs/        #   respostas reais da API, gravadas para os testes
│
├── local/                                  # AMBIENTE LOCAL (nível 2)
│   ├── docker-compose.yml                  #   moto (S3, SSM, EventBridge) + container da Lambda + Marquez
│   ├── Dockerfile                          #   imagem public.ecr.aws/lambda/python com o pacote
│   ├── seed.sh                             #   simula os contratos do foundation e do lakehouse no moto
│   └── verify.sh                           #   confere arquivo, manifesto, quarentena e evento
│
├── schemas/
│   └── pipeline.schema.json                # formato dos arquivos de pipelines/
│
├── docs/
│   └── runbooks/financeiro/bcb/            # procedimentos por fonte: falha, reprocessamento, quarentena
│
├── build/                                  # gerado pelo make build (fora do Git)
├── pyproject.toml                          # dependências, pytest, ruff
├── Makefile
├── CLAUDE.md
└── README.md
```

O pacote `labdata` tem três pilares, com nomes que não se confundem:

| Pilar | Responde | Import |
|---|---|---|
| `assets/` | **O que** é cada dado (constantes lidas dos contratos) | `from labdata.assets.bronze.financeiro import bcb` |
| `sdk/` | **Como** a ingestão funciona (framework comum) | `from labdata.sdk.core import Extractor` |
| `extract/` | **Como** buscar cada fonte (classes `Extractor`) | `from labdata.extract.financeiro.bcb import Sgs` |

A camada de asset `source` (fonte externa, em `assets/source/`) é o **dado** de origem; o `extract/` é o **código** que o busca.

### Regras da estrutura

1. **O `sdk/` não conhece o `extract/`, e o `extract/` não reimplementa o `sdk/`.** Uma fonte nova só implementa o `extract()`; gravar no bronze, validar, mandar para a quarentena, logar e publicar o evento vêm do `sdk/`.
2. **Só o `sdk/adapters/` fala com o mundo externo** (AWS, HTTP). `core/`, `layers/` e `governance/` não importam `boto3`: são testados sem rede, e o mesmo código pode rodar no Airflow trocando só o `runtime/`. É a arquitetura de **portas e adaptadores**.
3. **Asset ≠ pipeline.** O asset diz *o que* é o dado (contrato); a pipeline diz *como e quando* ele é produzido. Um asset tem uma pipeline que o produz.
4. **A hierarquia é sempre `<domínio>/<fonte>/<entidade>`**, igual em `extract/`, `pipelines/`, `tests/`, `fixtures/` e `docs/runbooks/`. Achou a pasta de uma fonte num lugar, acha em todos.
5. **Toda regra sobre o dado mora em `sdk/governance/`**: contrato, qualidade, quarentena, linhagem e classificação. As camadas (`layers/`) e as fontes usam essas regras, mas não as redefinem.
6. **`layers/` segue a arquitetura medalhão**: cada camada é uma pasta (`bronze/`, e no futuro outras, se houver código Python para elas), mesmo que hoje só exista uma.
7. **Pasta só existe quando tem conteúdo.** A `cvm/` entra na etapa 4b, e não antes; a `silver/` em `layers/`, só se a silver tiver código neste pacote.
8. **Os nomes principais são reexportados no `__init__.py` de cada pacote**, para os imports não ficarem longos (`from labdata.sdk.layers.bronze import BronzeWriter`). Exceção: `labdata/` e `labdata/assets/` **não têm `__init__.py`**, porque são *namespace packages* compartilhados com outros repositórios ([padrão de assets](https://github.com/lab-data-platform/data-platform/blob/main/docs/assets.md#4-lib-de-assets)).
9. **Nenhum ID ou nome físico escrito à mão.** Caminho no S3, tabela no Glue, URI e identidade OpenLineage vêm sempre da lib (`bcb.sgs.s3_prefix`, `bcb.sgs.table`...), que os deriva do ID do contrato.

### Como fica adicionar uma fonte

Exemplo: o informe diário da CVM.

| # | Arquivo | O quê |
|---|---|---|
| 1 | `src/labdata/extract/financeiro/cvm/inf_diario.py` | `class InfDiario(Extractor)` com o `extract()` |
| 2 | `assets/bronze/financeiro/cvm/inf_diario.yml` | Contrato ODCS do `bronze.financeiro.cvm.inf_diario` (a constante na lib `labdata.assets` sai dele) |
| 3 | `pipelines/financeiro/cvm/inf_diario.yml` | Handler, agenda, memória, timeout |
| 4 | `tests/unit/extract/financeiro/cvm/test_inf_diario.py` | Teste com a fixture gravada |
| 5 | `docs/runbooks/financeiro/cvm/inf_diario.md` | Procedimentos operacionais |

Nenhum arquivo do `sdk/` nem do `infra/` muda: o CI valida os YAMLs, e o `make apply` cria os recursos.

---

## Como o dado fica salvo

O código fica no repositório; o **dado** fica no bucket do bronze (contrato `/lab-data/<env>/lakehouse/bronze_bucket`):

```
s3://lab-data-dev-bronze-<account_id>/
├── financeiro/bcb/sgs/                                       ← asset bronze.financeiro.bcb.sgs
│   └── serie=432/                                            ← partição da fonte (ex.: cada série do SGS)
│       └── ingestion_date=2026-11-02/                        ← partição da ingestão
│           ├── 2016-11-02_2026-11-02.json                    ← arquivo COMO VEIO da API, sem alteração
│           └── _manifest.json                                ← colunas técnicas e estatísticas
└── _quarantine/financeiro/bcb/sgs/ingestion_date=2026-11-02/ ← o que falhou na validação, com o motivo
```

- **Reexecutar o mesmo dia substitui** a mesma pasta, e nunca duplica ([governança](https://github.com/lab-data-platform/data-platform/blob/main/docs/governanca.md#5-idempotência-e-reprocessamento)).
- O **manifesto** guarda `_ingested_at`, `_source`, `_run_id`, `_source_file`, `_partition`, a quantidade de registros e o hash do conteúdo.
- A tabela `lab_data_dev_bronze.bcb_sgs` no Glue aponta para `financeiro/bcb/sgs/` e lê as partições pelo caminho. Os dois nomes são derivados do ID ([nomes físicos](https://github.com/lab-data-platform/data-platform/blob/main/docs/assets.md#2-nomes-físicos-derivados)).

---

## Recursos na AWS (previstos)

Nada foi criado ainda. **Uma linha por pipeline** em cada recurso. **Região:** `us-east-2` (Ohio).

| Serviço AWS | Recurso | Para que serve | Região | Custo | Código | Onde ver no console |
|---|---|---|---|---|---|---|
| **AWS Lambda** | Funções `lab-data-dev-ingest-<fonte>-<entidade>` | Extrair e validar | `us-east-2` | grátis no volume do lab | `infra/modules/pipeline/lambda.tf` | Lambda → Functions |
| **AWS Step Functions** | State machine `lab-data-dev-ingest-<fonte>-<entidade>` | Extrair → validar → registrar → publicar, com retry, quarentena e alerta | `us-east-2` | grátis (4 mil transições/mês) | `infra/modules/pipeline/state_machine.tf` | Step Functions → State machines |
| **Amazon EventBridge Scheduler** | Agenda por pipeline | Dispara a state machine | `us-east-2` | grátis | `infra/modules/pipeline/schedule.tf` | EventBridge → Schedules |
| **AWS IAM** | Roles da Lambda, da state machine e da agenda | Permissão mínima por pipeline | global | grátis | `infra/modules/pipeline/iam.tf` | IAM → Roles |
| **AWS Glue** (Data Catalog) | Tabela bronze por asset | Torna o dado bruto consultável pelo Athena | `us-east-2` | grátis | `infra/modules/pipeline/catalog.tf` | Glue → Tables |
| **Amazon CloudWatch** | Log groups | Logs das execuções, com retenção curta | `us-east-2` | centavos | `infra/modules/pipeline/lambda.tf` | CloudWatch → Log groups |
| **AWS Systems Manager** | Parâmetros em `/lab-data/dev/ingestion/` | ARN de cada state machine, para quem precisar disparar | `us-east-2` | grátis | `infra/contract.tf` | Parameter Store |

## Depende de

| Repositório | O que usa |
|---|---|
| `data-foundation` | `alerts_topic_arn` (alertas) e `assets_event_bus_name`/`_arn` (eventos) |
| `data-lakehouse` | `bronze_bucket`, `glue_database_bronze` e `athena_workgroup` |
| `data-platform` | Padrão de assets e schemas de validação (`asset-extensions.schema.json`, `asset-updated.schema.json`), numa versão fixa |

---

## Uso (previsto)

```bash
make help            # lista os comandos

# Nível 1: sem AWS
make test            # pytest (unit + contracts) + terraform test
make lint            # ruff

# Nível 2: sem AWS, no runtime real da Lambda
make local-up        # sobe o moto e o container da Lambda
make local-test      # invoca a Lambda no container e confere o resultado no moto
make local-down

# Nível 3: conta real
make build           # gera build/ingestion.zip
make init · make plan · make apply
make run PIPELINE=financeiro/bcb/sgs   # dispara uma execução na conta
```

## Testes

| Nível | Onde | O que cobre |
|---|---|---|
| 1. Unitário | `tests/unit/`, `tests/contracts/`, `infra/tests/` | Regras do `sdk/` sem rede, `extract()` de cada fonte com fixtures, contratos ODCS válidos (`datacontract lint` + extensões), lib de assets, Terraform com provider simulado |
| 2. Integração local | `tests/integration/` + `local/` | A Lambda no **container oficial da AWS**, gravando no S3 e publicando no EventBridge do **moto**; eventos OpenLineage visíveis no **Marquez** |
| 3. Real | `make run` | Execução na conta, com o fluxo inteiro visível no console do Step Functions |

## Qualidade

| Verificação | Onde roda | O que cobre |
|---|---|---|
| Pré-commit | Na sua máquina, a cada `git commit` | Segredos (gitleaks, credenciais AWS, chaves privadas), YAML, espaços e fim de arquivo, commit direto na `main`; previsto: ruff, `datacontract lint` e validação das extensões em `assets/` e dos arquivos de `pipelines/` |
| CI | GitHub Actions ([ci.yml](.github/workflows/ci.yml)), em todo PR e push na `main` e na `develop` | O mesmo pre-commit; previsto: jobs de Python (ruff + pytest), Terraform e integração local; todos obrigatórios para o merge |

```bash
pre-commit install            # uma vez por clone: ativa os hooks
pre-commit run --all-files    # roda todos os hooks manualmente
```
