"""Todo arquivo em pipelines/ é válido e aponta para um asset com contrato e um extrator que existe."""

import importlib
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from conftest import ROOT, load_schema

PIPELINES = sorted((ROOT / "pipelines").rglob("*.yml"))
SCHEMA = Draft202012Validator(load_schema("pipeline.schema.json"))


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


@pytest.mark.parametrize("path", PIPELINES, ids=relative)
def test_format(path):
    assert [e.message for e in SCHEMA.iter_errors(yaml.safe_load(path.read_text()))] == []


@pytest.mark.parametrize("path", PIPELINES, ids=relative)
def test_name_matches_the_path(path):
    p = yaml.safe_load(path.read_text())
    assert Path(p["pipeline"] + ".yml") == path.relative_to(ROOT / "pipelines")


@pytest.mark.parametrize("path", PIPELINES, ids=relative)
def test_pipeline_path_is_the_asset_path(path):
    p = yaml.safe_load(path.read_text())
    assert p["asset"] == "bronze." + p["pipeline"].replace("/", ".")


@pytest.mark.parametrize("path", PIPELINES, ids=relative)
def test_asset_has_contract_and_extractor_exists(path):
    from labdata.sdk.governance.contracts.assets import load_asset

    p = yaml.safe_load(path.read_text())
    load_asset(p["asset"])
    module_name, class_name = p["extractor"]["class"].split(":")
    extractor = getattr(importlib.import_module(module_name), class_name)(**p["extractor"].get("params", {}))
    assert extractor.asset_id == p["asset"]
    load_asset(extractor.source_asset_id)
