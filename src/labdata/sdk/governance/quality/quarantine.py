"""Quarentena: o que falha na validação vai para _quarantine/, com o motivo, e não chega ao bronze."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from labdata.sdk.core.models import RawFile, RunContext
from labdata.sdk.core.ports import ObjectStore

REASON_FILE = "_reason.json"


def quarantine(store: ObjectStore, *, prefix: str, files: list[RawFile], reasons: list[str], run: RunContext) -> str:
    """Grava os arquivos e um `_reason.json` em `prefix`. Devolve a URI da quarentena."""
    for f in files:
        store.put(prefix + f.name, f.content, f.content_type)
    reason = {
        "_run_id": run.run_id,
        "pipeline": run.pipeline,
        "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reasons": reasons,
    }
    store.put(prefix + REASON_FILE, json.dumps(reason, ensure_ascii=False, indent=2).encode("utf-8"))
    return store.uri(prefix)
