"""Grava uma partição do bronze: os arquivos como vieram + o manifesto.

Carga "substituir": antes de gravar, apaga o que já existe na partição. Reexecutar o mesmo dia troca a
partição inteira, e nunca duplica (governança, seção 5).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from labdata.sdk.core.models import RawFile, RunContext
from labdata.sdk.core.ports import ObjectStore
from labdata.sdk.governance.lineage.manifest import build_manifest, to_bytes
from labdata.sdk.layers.bronze.layout import BronzeLayout


class BronzeWriter:
    def __init__(self, store: ObjectStore):
        self.store = store

    def write(
        self,
        *,
        layout: BronzeLayout,
        reference_date: date,
        files: list[RawFile],
        run: RunContext,
        source_asset_id: str,
        request_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Substitui a partição e devolve o manifesto gravado."""
        prefix = layout.partition_prefix(reference_date)
        existing = self.store.list(prefix)
        if existing:
            self.store.delete(existing)

        written = []
        for f in files:
            key = prefix + f.name
            self.store.put(key, f.content, f.content_type)
            written.append((f, self.store.uri(key)))

        manifest = build_manifest(
            asset_id=layout.asset.id,
            source_asset_id=source_asset_id,
            contract_version=layout.asset.version,
            partition=layout.partition(reference_date),
            files=written,
            run=run,
            request_params=request_params,
        )
        self.store.put(layout.manifest_key(reference_date), to_bytes(manifest))
        return manifest
