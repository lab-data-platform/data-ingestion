"""Regras de qualidade do contrato e validação."""

import pytest

from labdata.sdk.core import RawFile, ValidationFailed
from labdata.sdk.governance.contracts.assets import load_asset
from labdata.sdk.governance.quality.rules import check_library, check_required
from labdata.sdk.governance.quality.validator import validate

SCHEMA = ({"name": "data", "required": True}, {"name": "valor", "required": True}, {"name": "obs"})


def test_required_column_empty_or_missing():
    reasons = check_required([{"data": "29/10/2026", "valor": ""}, {"data": "30/10/2026"}], SCHEMA)
    assert reasons == ["coluna obrigatória 'valor' vazia ou ausente em 2 registro(s)"]


def test_row_count():
    assert check_library([{}], {"metric": "rowCount", "mustBe": 1}) == []
    assert check_library([{}, {}], {"metric": "rowCount", "mustBe": 1}) == ["rowCount = 2, esperado = 1"]
    assert check_library([], {"metric": "rowCount", "mustBeGreaterThan": 0}) == ["rowCount = 0, esperado > 0"]


def test_unknown_metric_is_reported():
    assert check_library([], {"metric": "nullCount"}) == ["regra de qualidade não suportada: metric='nullCount'"]


def test_validation_with_the_cdi_contract():
    asset = load_asset("bronze.bcb.sgs.cdi_diario")
    ok = RawFile(name="data.json", content=b"", records=[{"data": "29/10/2026", "valor": "0.050788"}])
    validate(asset, [ok])
    two = RawFile(name="data.json", content=b"", records=[{"data": "a", "valor": "1"}, {"data": "b", "valor": "2"}])
    with pytest.raises(ValidationFailed) as e:
        validate(asset, [two])
    assert e.value.reasons == ["rowCount = 2, esperado = 1"]
