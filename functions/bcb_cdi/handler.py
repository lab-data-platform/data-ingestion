"""Lambda do CDI diário: busca a série 12 do SGS (Banco Central) e grava no bronze.

Evento de entrada:
    {"reference_date": "2026-10-30"}   → busca esse dia (reprocessamento)
    {}                                 → busca o dia útil anterior (execução agendada)

Grava em:
    s3://<bucket do bronze>/bcb/sgs/cdi_diario/reference_date=AAAA-MM-DD/data.jsonl

Rodar de novo o mesmo dia sobrescreve o mesmo arquivo: não duplica.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import boto3

SERIES = 12  # CDI diário no SGS
API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?formato=json&dataInicial={start}&dataFinal={end}"
PREFIX = "bcb/sgs/cdi_diario"
TIMEZONE = ZoneInfo("America/Sao_Paulo")


def previous_business_day(today: date) -> date:
    """Dia útil anterior, sem considerar feriados (num feriado a API só devolve vazio)."""
    day = today - timedelta(days=1)
    while day.weekday() >= 5:  # 5 = sábado, 6 = domingo
        day -= timedelta(days=1)
    return day


def fetch(reference_date: date) -> list[dict]:
    """Busca as observações do dia na API. Lista vazia quando não há dado (fim de semana, feriado)."""
    # A API recusa início igual ao fim (HTTP 400): pede D até D+1 e depois fica só com D.
    url = API_URL.format(
        series=SERIES,
        start=reference_date.strftime("%d/%m/%Y"),
        end=(reference_date + timedelta(days=1)).strftime("%d/%m/%Y"),
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            rows = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:  # a API responde 404 quando a janela não tem dado
            return []
        raise

    wanted = reference_date.strftime("%d/%m/%Y")
    return [row for row in rows if row["data"] == wanted]


def save(rows: list[dict], reference_date: date) -> str:
    """Grava as linhas em JSON Lines (um objeto por linha, o formato que o Athena lê)."""
    bucket = os.environ["BRONZE_BUCKET"]
    key = f"{PREFIX}/reference_date={reference_date.isoformat()}/data.jsonl"
    body = "".join(json.dumps(row) + "\n" for row in rows)

    boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
    return f"s3://{bucket}/{key}"


def handler(event, context):
    if event.get("reference_date"):
        reference_date = date.fromisoformat(event["reference_date"])
    else:
        reference_date = previous_business_day(datetime.now(TIMEZONE).date())

    rows = fetch(reference_date)
    if not rows:
        result = {"status": "no_data", "reference_date": reference_date.isoformat()}
    else:
        location = save(rows, reference_date)
        result = {"status": "ok", "reference_date": reference_date.isoformat(), "records": len(rows), "location": location}

    print(json.dumps(result))  # o print vai para o CloudWatch Logs
    return result
