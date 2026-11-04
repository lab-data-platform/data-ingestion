# CLAUDE.md — data-ingestion

Repositório da ingestão da plataforma `lab-data`. Regras gerais ficam no hub: [../data-platform/CLAUDE.md](../data-platform/CLAUDE.md).

## Específico deste repositório

- **Recomeço do zero (2026-11-03).** A versão anterior (sdk próprio, contratos ODCS, lib de assets, Step Functions) foi descartada. Não a use como referência nem a recrie.
- **Papel:** exercício de Lambda (CDI diário do BCB → bronze, `functions/bcb_cdi/handler.py` + `infra/bcb_cdi.tf`), concluído e destruído em 2026-11-03. **Não é a ferramenta de ingestão da plataforma**: a ingestão vai para o Airflow. Não evolua este repositório como ingestão sem o usuário pedir.
- **Simplicidade:** um arquivo Python por Lambda, sem dependências (urllib + boto3 do runtime); Terraform direto, sem módulos. Nada de framework, contrato ou abstração sem o usuário pedir.
- **Caminho no bronze:** `bcb/sgs/cdi_diario/reference_date=AAAA-MM-DD/data.jsonl` (JSON Lines).
- **API do SGS:** janela D → D+1 (a API recusa D → D), 404 quando não há dado, data em dd/mm/aaaa.
- Antes de entregar: `make test` e `make validate`.
