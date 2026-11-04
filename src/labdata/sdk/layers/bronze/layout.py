"""Caminhos do bronze, derivados do ID do asset (data-platform/docs/assets.md, seção 2).

<origem>/<níveis...>/<entidade>/reference_date=<AAAA-MM-DD>/
_quarantine/<origem>/<níveis...>/<entidade>/reference_date=<AAAA-MM-DD>/
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from labdata.sdk.governance.contracts.assets import Asset

MANIFEST = "_manifest.json"


@dataclass(frozen=True)
class BronzeLayout:
    asset: Asset

    def partition(self, reference_date: date) -> str:
        return f"reference_date={reference_date.isoformat()}"

    def partition_prefix(self, reference_date: date) -> str:
        return f"{self.asset.s3_prefix}{self.partition(reference_date)}/"

    def quarantine_prefix(self, reference_date: date) -> str:
        return f"_quarantine/{self.partition_prefix(reference_date)}"

    def manifest_key(self, reference_date: date) -> str:
        return self.partition_prefix(reference_date) + MANIFEST
