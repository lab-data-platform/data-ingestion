"""Modelos que circulam entre as fontes, as camadas e a governança. Sem nenhuma dependência da AWS."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class ExtractRequest:
    """O que uma execução pede à fonte."""

    reference_date: date
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawFile:
    """Um arquivo como veio da fonte, pronto para ir ao bronze."""

    name: str
    content: bytes
    records: list[dict[str, Any]]
    content_type: str = "application/json"
    source_uri: str = ""

    @property
    def sha256(self) -> str:
        return "sha256:" + hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class RunContext:
    """Identifica a execução: liga o dado gravado ao log, ao OpenLineage e ao evento."""

    run_id: str
    pipeline: str
    started_at: datetime


@dataclass(frozen=True)
class ExtractResult:
    """O que a execução produziu. Vira a saída da Lambda e o detail do AssetUpdated."""

    status: str  # "ok" | "no_data" | "quarantined"
    asset: str
    partition: str
    location: str = ""
    contract_version: str = ""
    load: str = "replace"  # "replace" | "upsert" | "append"
    stats: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
