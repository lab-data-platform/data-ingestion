"""O handler da Lambda de ponta a ponta, com o S3 emulado pelo moto (em memória)."""

import json
from datetime import date

import boto3
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from moto import mock_aws

from conftest import fixture_bytes, load_schema

BUCKET = "lab-data-dev-bronze-123456789012"
PREFIX = "bcb/sgs/cdi_diario/"


@pytest.fixture
def environment(monkeypatch):
    monkeypatch.setenv("LABDATA_PIPELINE", "bcb/sgs/cdi_diario")
    monkeypatch.setenv("BRONZE_BUCKET", BUCKET)
    monkeypatch.setenv("OPENLINEAGE_DISABLED", "true")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-2")
    for var in ("AWS_PROFILE", "AWS_ENDPOINT_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "us-east-2"})
        yield


def fake_api(monkeypatch, status, body):
    monkeypatch.setattr("labdata.sdk.adapters.http.client.UrllibClient.get", lambda self, url: (status, body))


def keys():
    return sorted(o["Key"] for o in boto3.client("s3").list_objects_v2(Bucket=BUCKET).get("Contents", []))


def test_ok_writes_to_s3_and_returns_asset_updated(environment, monkeypatch):
    from labdata.sdk.runtime.lambda_handler import handler

    fake_api(monkeypatch, 200, fixture_bytes("bcb", "sgs", "cdi_diario", "window_two_business_days.json"))
    output = handler({"run_id": "arn:execution:1", "reference_date": "2026-10-29"}, None)

    assert output["status"] == "ok"
    assert keys() == [
        PREFIX + "reference_date=2026-10-29/_manifest.json",
        PREFIX + "reference_date=2026-10-29/data.json",
    ]
    validator = Draft202012Validator(
        load_schema("platform", "asset-updated.schema.json"), format_checker=FormatChecker()
    )
    assert list(validator.iter_errors(output["asset_updated"])) == []
    json.dumps(output)  # a saída precisa ser serializável para a state machine


def test_weekend_returns_no_data(environment, monkeypatch):
    from labdata.sdk.runtime.lambda_handler import handler

    fake_api(monkeypatch, 404, b"{}")
    output = handler({"run_id": "arn:execution:2", "reference_date": "2026-10-31"}, None)
    assert output["status"] == "no_data" and "asset_updated" not in output
    assert keys() == []


def test_without_date_uses_the_previous_business_day(environment, monkeypatch):
    from labdata.sdk.runtime import lambda_handler

    fake_api(monkeypatch, 404, b"{}")
    monkeypatch.setattr(lambda_handler, "reference_date", lambda rule, timezone: date(2026, 10, 30))
    output = lambda_handler.handler({"run_id": "arn:execution:3"}, None)
    assert output["reference_date"] == "2026-10-30"
