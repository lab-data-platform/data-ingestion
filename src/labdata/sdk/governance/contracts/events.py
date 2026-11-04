"""Evento AssetUpdated: o que o produtor publica quando um asset fica pronto (data-platform/docs/eventos.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from labdata.sdk.core.models import ExtractResult, RunContext

DETAIL_TYPE = "AssetUpdated"
SOURCE = "lab-data.ingestion"


def asset_updated_detail(result: ExtractResult, run: RunContext, produced_at: datetime | None = None) -> dict[str, Any]:
    """Monta o `detail` do evento a partir do resultado da execução. Só faz sentido com status "ok"."""
    if result.status != "ok":
        raise ValueError(f"AssetUpdated só é publicado para status 'ok' (recebido {result.status!r})")
    detail: dict[str, Any] = {
        "asset": result.asset,
        "contract_version": result.contract_version,
        "partition": result.partition,
        "load": result.load,
        "location": result.location,
        "run_id": run.run_id,
        "produced_at": (produced_at or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if result.stats:
        detail["stats"] = result.stats
    return detail
