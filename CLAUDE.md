# CLAUDE.md — data-ingestion

Repositório da ingestão da plataforma `lab-data`. Regras gerais, arquitetura e contratos ficam no hub: [../data-platform/CLAUDE.md](../data-platform/CLAUDE.md). Leia esse arquivo primeiro.

## Específico deste repositório

- **Status: camada 4 em construção.** Primeira pipeline: CDI diário (`bronze.bcb.sgs.cdi_diario`), testada nos níveis 1 e 2. Falta o Terraform (`infra/`).
- **Estrutura aprovada no README:** siga a árvore e as 10 regras de lá. Pacote `src/labdata/` com `assets/` (lib), `sdk/` (framework) e `extractors/` (código por origem e sistema).
- **Idioma dos nomes (ADR-0022):** código, chaves, campos e valores em inglês; texto para pessoas em português; colunas da fonte com o nome original.
- **IDs e caminhos:** o ID do asset é um caminho, `<camada>.<origem>[.<nível>...].<entidade>`, **sem domínio** (ADR-0021). O domínio só aparece no campo `domain` do contrato. A hierarquia das pastas é o caminho do asset.
- **Nunca escreva ID ou nome físico à mão** no código: use o asset carregado do contrato (`s3_prefix`, `table`, `uri`).
- `labdata/` e `labdata/assets/` não têm `__init__.py` (namespace packages). Não crie esses arquivos.
- Os schemas em `schemas/platform/` são cópias fixadas do `data-platform`; ao atualizá-los, atualize também o arquivo `ORIGEM`.
- Antes de entregar uma mudança: `make lint`, `make test`, `make contracts` e o ciclo local (`make local-up`, `make local-test`, `make local-down`).
- Depende dos contratos do `data-foundation` e do `data-lakehouse` (o bronze precisa estar aplicado).
