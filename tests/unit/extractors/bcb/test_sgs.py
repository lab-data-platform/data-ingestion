"""Extrator do SGS, com respostas reais da API gravadas em tests/fixtures."""

from datetime import date

import pytest

from conftest import FakeHttp, fixture_bytes
from labdata.extractors.bcb import Sgs
from labdata.sdk.core import ExtractRequest, NoData, SourceUnavailable


def make_extractor(status, body):
    http = FakeHttp(status, body)
    sgs = Sgs(series=12, asset_id="bronze.bcb.sgs.cdi_diario", source_asset_id="source.bcb.sgs.cdi_diario", http=http)
    return sgs, http


def fixture(name):
    return fixture_bytes("bcb", "sgs", "cdi_diario", name)


def test_requests_window_from_d_to_d_plus_1():
    sgs, http = make_extractor(200, fixture("window_two_business_days.json"))
    sgs.extract(ExtractRequest(reference_date=date(2026, 10, 29)))
    assert http.urls == [
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial=29/10/2026&dataFinal=30/10/2026"
    ]


def test_between_two_business_days_keeps_only_the_reference_date():
    sgs, _ = make_extractor(200, fixture("window_two_business_days.json"))  # a API devolve 29/10 e 30/10
    [file] = sgs.extract(ExtractRequest(reference_date=date(2026, 10, 29)))
    assert file.records == [{"data": "29/10/2026", "valor": "0.050788"}]
    assert file.name == "data.json"


def test_friday_to_saturday_returns_friday():
    sgs, _ = make_extractor(200, fixture("window_friday_saturday.json"))
    [file] = sgs.extract(ExtractRequest(reference_date=date(2026, 10, 30)))
    assert file.records == [{"data": "30/10/2026", "valor": "0.050788"}]


def test_404_means_no_data_not_failure():
    sgs, _ = make_extractor(404, fixture("window_weekend_404.json"))
    with pytest.raises(NoData):
        sgs.extract(ExtractRequest(reference_date=date(2026, 10, 31)))


def test_window_without_the_requested_day_means_no_data():
    sgs, _ = make_extractor(200, fixture("window_friday_saturday.json"))  # só tem 30/10
    with pytest.raises(NoData):
        sgs.extract(ExtractRequest(reference_date=date(2026, 10, 31)))


def test_other_status_means_source_unavailable():
    sgs, _ = make_extractor(400, b'{"erro":"DataFinal deve ser maior que dataInicial."}')
    with pytest.raises(SourceUnavailable):
        sgs.extract(ExtractRequest(reference_date=date(2026, 10, 30)))


def test_lineage_points_to_the_series_in_the_api():
    sgs, _ = make_extractor(200, b"[]")
    assert (sgs.lineage_namespace, sgs.lineage_name) == ("https://api.bcb.gov.br", "/dados/serie/bcdata.sgs.12")
