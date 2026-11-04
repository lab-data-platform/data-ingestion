"""O detail do AssetUpdated cumpre o schema da plataforma."""

from datetime import UTC, datetime

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from conftest import load_schema
from labdata.sdk.core import ExtractResult
from labdata.sdk.governance.contracts.events import asset_updated_detail

RESULT = ExtractResult(
    status="ok",
    asset="bronze.bcb.sgs.cdi_diario",
    partition="reference_date=2026-10-29",
    location="s3://bucket/bcb/sgs/cdi_diario/reference_date=2026-10-29/",
    contract_version="1.0.0",
    stats={"records": 1, "files": 1, "bytes": 42, "hash": "sha256:abc"},
)


def test_detail_matches_the_platform_schema(run):
    detail = asset_updated_detail(RESULT, run, produced_at=datetime(2026, 11, 3, 13, 0, 5, tzinfo=UTC))
    schema = load_schema("platform", "asset-updated.schema.json")
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(detail))
    assert errors == []
    assert detail["run_id"] == run.run_id and detail["load"] == "replace"


def test_only_published_for_status_ok(run):
    with pytest.raises(ValueError):
        asset_updated_detail(ExtractResult(status="no_data", asset=RESULT.asset, partition="x"), run)
