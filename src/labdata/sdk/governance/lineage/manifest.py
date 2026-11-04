"""Manifesto gravado ao lado de cada partição do bronze, com as colunas técnicas da plataforma.

O arquivo de dado fica como veio da fonte; as colunas técnicas (governança, seção 3) vivem aqui.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from labdata.sdk.core.models import RawFile, RunContext


def build_manifest(
    *,
    asset_id: str,
    source_asset_id: str,
    contract_version: str,
    partition: str,
    files: list[tuple[RawFile, str]],
    run: RunContext,
    request_params: dict[str, Any],
    ingested_at: datetime | None = None,
) -> dict[str, Any]:
    """`files` = lista de (arquivo, uri onde foi gravado)."""
    return {
        "_ingested_at": (ingested_at or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_source": source_asset_id,
        "_run_id": run.run_id,
        "_partition": partition,
        "asset": asset_id,
        "contract_version": contract_version,
        "pipeline": run.pipeline,
        "request": request_params,
        "files": [
            {
                "_source_file": uri,
                "source_uri": raw.source_uri,
                "records": len(raw.records),
                "bytes": len(raw.content),
                "hash": raw.sha256,
            }
            for raw, uri in files
        ],
        "stats": statistics([raw for raw, _ in files]),
    }


def statistics(files: list[RawFile]) -> dict[str, Any]:
    """Estatísticas do conteúdo, usadas no manifesto e no evento AssetUpdated."""
    joined = b"".join(f.content for f in files)
    return {
        "records": sum(len(f.records) for f in files),
        "files": len(files),
        "bytes": len(joined),
        "hash": "sha256:" + hashlib.sha256(joined).hexdigest(),
    }


def to_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
