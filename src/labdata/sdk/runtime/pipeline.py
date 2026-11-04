"""O fluxo de uma execução, igual para toda fonte.

extrair → validar → gravar no bronze (ou quarentena) → linhagem → resultado

O resultado vira a saída da Lambda; a state machine decide pelo `status`:
- "ok": publica o AssetUpdated (integração nativa com o EventBridge);
- "no_data": termina com sucesso, sem evento;
- "quarantined": alerta e termina, sem evento.
Erros de fonte (`SourceUnavailable`) sobem para a state machine, que tenta de novo e alerta.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date
from typing import Any

from labdata.sdk.core.errors import NoData, ValidationFailed
from labdata.sdk.core.extractor import Extractor
from labdata.sdk.core.models import ExtractRequest, ExtractResult, RunContext
from labdata.sdk.core.ports import ObjectStore
from labdata.sdk.governance.contracts.assets import Asset, load_asset
from labdata.sdk.governance.lineage.manifest import statistics
from labdata.sdk.governance.lineage.openlineage import Lineage
from labdata.sdk.governance.quality.quarantine import quarantine
from labdata.sdk.governance.quality.validator import validate
from labdata.sdk.layers.bronze.layout import BronzeLayout
from labdata.sdk.layers.bronze.writer import BronzeWriter
from labdata.sdk.runtime.logging import info

log = logging.getLogger(__name__)


def run_pipeline(
    *,
    extractor: Extractor,
    store: ObjectStore,
    run: RunContext,
    reference_date: date,
    params: dict[str, Any] | None = None,
    lineage: Lineage | None = None,
    asset: Asset | None = None,
) -> ExtractResult:
    asset = asset or load_asset(extractor.asset_id)
    layout = BronzeLayout(asset)
    request = ExtractRequest(reference_date=reference_date, params=params or {})
    partition = layout.partition(reference_date)
    info(log, "início da execução", asset=asset.id, partition=partition)

    if lineage:
        lineage.start()
    try:
        try:
            files = extractor.extract(request)
        except NoData as e:
            info(log, "fonte sem dado para a data", asset=asset.id, partition=partition, reason=str(e))
            if lineage:
                lineage.complete()
            return ExtractResult(status="no_data", asset=asset.id, partition=partition, reason=str(e))

        try:
            validate(asset, files)
        except ValidationFailed as e:
            location = quarantine(
                store, prefix=layout.quarantine_prefix(reference_date), files=files, reasons=e.reasons, run=run
            )
            info(log, "dado em quarentena", asset=asset.id, partition=partition, reasons=e.reasons, location=location)
            if lineage:
                lineage.fail()
            return ExtractResult(
                status="quarantined",
                asset=asset.id,
                partition=partition,
                location=location,
                contract_version=asset.version,
                reason=str(e),
            )

        BronzeWriter(store).write(
            layout=layout,
            reference_date=reference_date,
            files=files,
            run=run,
            source_asset_id=extractor.source_asset_id,
            request_params={"reference_date": reference_date.isoformat(), **request.params},
        )
        result = ExtractResult(
            status="ok",
            asset=asset.id,
            partition=partition,
            location=store.uri(layout.partition_prefix(reference_date)),
            contract_version=asset.version,
            load="replace",
            stats=statistics(files),
        )
        info(log, "partição gravada", **asdict(result))
        if lineage:
            lineage.complete()
        return result
    except Exception:
        if lineage:
            lineage.fail()
        raise
