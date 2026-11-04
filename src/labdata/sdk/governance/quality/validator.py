"""Aplica as regras do contrato aos arquivos extraídos."""

from __future__ import annotations

from labdata.sdk.core.errors import ValidationFailed
from labdata.sdk.core.models import RawFile
from labdata.sdk.governance.contracts.assets import Asset
from labdata.sdk.governance.quality.rules import check_quality, check_required


def validate(asset: Asset, files: list[RawFile]) -> None:
    """Levanta `ValidationFailed` com todos os motivos, se o dado não cumprir o contrato."""
    records = [r for f in files for r in f.records]
    reasons = check_required(records, asset.schema) + check_quality(records, asset.quality)
    if reasons:
        raise ValidationFailed(reasons)
