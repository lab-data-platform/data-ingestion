"""Handler genérico de Lambda: o mesmo para toda pipeline.

A Lambda sabe qual pipeline é pela variável LABDATA_PIPELINE; o resto vem de pipelines/<pipeline>.yml.

Evento de entrada (enviado pela state machine, ou num teste local):
    {"run_id": "<arn da execução>", "reference_date": "2026-10-30"}   # reference_date é opcional

Saída: o ExtractResult como dicionário, mais o run_id e o detail do AssetUpdated quando status = "ok".
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any

from labdata.sdk.adapters.aws.s3 import S3Store
from labdata.sdk.core.models import RunContext
from labdata.sdk.governance.contracts.assets import load_asset
from labdata.sdk.governance.contracts.events import asset_updated_detail
from labdata.sdk.governance.lineage.openlineage import Lineage
from labdata.sdk.runtime import logging as jsonlog
from labdata.sdk.runtime.config import Environment, load_pipeline
from labdata.sdk.runtime.dates import reference_date
from labdata.sdk.runtime.pipeline import run_pipeline


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    env = Environment.from_env()
    config = load_pipeline(env.pipeline)
    run_id = event.get("run_id") or getattr(context, "aws_request_id", "local")
    jsonlog.configure(pipeline=config.pipeline, run_id=run_id)

    if event.get("reference_date"):
        ref_date = date.fromisoformat(event["reference_date"])
    else:
        ref_date = reference_date(config.reference_date_rule, timezone=config.timezone)

    extractor = config.build_extractor()
    asset = load_asset(config.asset)
    run = RunContext(run_id=run_id, pipeline=config.pipeline, started_at=datetime.now(UTC))
    lineage = Lineage(
        run=run,
        input_namespace=getattr(extractor, "lineage_namespace", "external"),
        input_name=getattr(extractor, "lineage_name", extractor.source_asset_id),
        output_namespace=f"s3://{env.bronze_bucket}",
        output_name=asset.openlineage_name(),
    )
    result = run_pipeline(
        extractor=extractor,
        store=S3Store(env.bronze_bucket),
        run=run,
        reference_date=ref_date,
        lineage=lineage,
        asset=asset,
    )

    output = {**asdict(result), "run_id": run_id, "reference_date": ref_date.isoformat()}
    if result.status == "ok":
        output["asset_updated"] = asset_updated_detail(result, run)
    return output
