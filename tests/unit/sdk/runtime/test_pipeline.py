"""O fluxo de uma execução: ok, sem dado, quarentena e falha da fonte."""

import json
from datetime import date

import pytest

from conftest import FakeHttp, fixture_bytes
from labdata.extractors.bcb import Sgs
from labdata.sdk.core import SourceUnavailable
from labdata.sdk.runtime.pipeline import run_pipeline

PREFIX = "bcb/sgs/cdi_diario/reference_date=2026-10-29/"


class LineageSpy:
    def __init__(self):
        self.events = []

    def start(self):
        self.events.append("START")

    def complete(self):
        self.events.append("COMPLETE")

    def fail(self):
        self.events.append("FAIL")


def execute(store, run, status, body, d=date(2026, 10, 29)):
    lineage = LineageSpy()
    sgs = Sgs(
        series=12,
        asset_id="bronze.bcb.sgs.cdi_diario",
        source_asset_id="source.bcb.sgs.cdi_diario",
        http=FakeHttp(status, body),
    )
    result = run_pipeline(extractor=sgs, store=store, run=run, reference_date=d, lineage=lineage)
    return result, lineage.events


def test_ok_writes_the_partition(store, run):
    body = fixture_bytes("bcb", "sgs", "cdi_diario", "window_two_business_days.json")
    result, events = execute(store, run, 200, body)
    assert result.status == "ok"
    assert result.location == f"s3://bucket-teste/{PREFIX}"
    assert result.stats["records"] == 1
    assert json.loads(store.get(PREFIX + "data.json")) == [{"data": "29/10/2026", "valor": "0.050788"}]
    assert events == ["START", "COMPLETE"]


def test_holiday_ends_with_no_data_and_writes_nothing(store, run):
    result, events = execute(store, run, 404, b"{}", d=date(2026, 10, 31))
    assert result.status == "no_data"
    assert store.objects == {}
    assert events == ["START", "COMPLETE"]


def test_data_outside_the_contract_is_quarantined(store, run):
    body = json.dumps([{"data": "29/10/2026", "valor": ""}]).encode()  # valor obrigatório vazio
    result, events = execute(store, run, 200, body)
    assert result.status == "quarantined"
    assert "valor" in result.reason
    assert store.list("bcb/") == []  # nada no bronze
    reason = json.loads(store.get("_quarantine/" + PREFIX + "_reason.json"))
    assert reason["_run_id"] == run.run_id
    assert events == ["START", "FAIL"]


def test_source_down_raises_to_the_state_machine(store, run):
    with pytest.raises(SourceUnavailable):
        execute(store, run, 503, b"")
