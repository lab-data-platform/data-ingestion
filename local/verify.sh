#!/usr/bin/env bash
# Invoca a Lambda no container oficial (como a state machine faria) e confere o resultado no moto.
set -euo pipefail
export AWS_ENDPOINT_URL=http://localhost:5100 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-2
unset AWS_PROFILE
BUCKET=lab-data-dev-bronze-123456789012
LAMBDA=http://localhost:9000/2015-03-31/functions/function/invocations
PREFIX=bcb/sgs/cdi_diario

failures=0
check() {
  if [[ "$3" == "$2" ]]; then echo "  ok    $1"; else echo "  FALHA $1: esperado '$2', obtido '$3'"; failures=$((failures + 1)); fi
}
invoke() { curl -s -X POST "$LAMBDA" -d "$1"; }
field() { python3 -c "import json,sys; print(json.load(sys.stdin).get('$1', ''))"; }
partition() { echo "s3://$BUCKET/$PREFIX/reference_date=$1"; }

echo "1. Dia útil (29/10, a API devolve 29 e 30): grava só o dia 29"
output=$(invoke '{"run_id": "local-1", "reference_date": "2026-10-29"}')
check "status ok" "ok" "$(echo "$output" | field status)"
check "data.json só com 29/10" '[{"data": "29/10/2026", "valor": "0.050788"}]' \
  "$(aws s3 cp "$(partition 2026-10-29)/data.json" - | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))')"
check "manifesto com o run_id" "local-1" "$(aws s3 cp "$(partition 2026-10-29)/_manifest.json" - | field _run_id)"
check "AssetUpdated na saída" "bronze.bcb.sgs.cdi_diario" \
  "$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["asset_updated"]["asset"])')"

echo "2. Reexecutar o mesmo dia: substitui, sem duplicar"
invoke '{"run_id": "local-2", "reference_date": "2026-10-29"}' >/dev/null
check "2 objetos na partição" "2" \
  "$(aws s3api list-objects-v2 --bucket $BUCKET --prefix $PREFIX/reference_date=2026-10-29/ --query 'length(Contents)')"
check "manifesto do novo run" "local-2" "$(aws s3 cp "$(partition 2026-10-29)/_manifest.json" - | field _run_id)"

echo "3. Fim de semana (31/10, API responde 404): termina sem dado e sem gravar"
output=$(invoke '{"run_id": "local-3", "reference_date": "2026-10-31"}')
check "status no_data" "no_data" "$(echo "$output" | field status)"
check "nenhuma partição de 31/10" "0" \
  "$(aws s3api list-objects-v2 --bucket $BUCKET --prefix $PREFIX/reference_date=2026-10-31/ --query 'length(Contents || `[]`)')"

if (( failures > 0 )); then echo "$failures verificação(ões) falharam."; exit 1; fi
echo "Tudo certo."
