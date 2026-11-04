"""Todo contrato em assets/ cumpre o padrão da plataforma (data-platform/docs/assets.md).

O formato ODCS em si é validado pelo `datacontract lint` (make contracts); aqui ficam as regras da plataforma.
"""

import importlib
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from conftest import ROOT, load_schema

CONTRACTS = sorted((ROOT / "assets").rglob("*.yml"))
SCHEMA = Draft202012Validator(load_schema("platform", "asset-extensions.schema.json"))


def read(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


@pytest.mark.parametrize("path", CONTRACTS, ids=relative)
def test_follows_the_platform_extensions(path):
    assert [e.message for e in SCHEMA.iter_errors(read(path))] == []


@pytest.mark.parametrize("path", CONTRACTS, ids=relative)
def test_file_path_matches_the_id(path):
    *folders, entity = read(path)["id"].split(".")
    assert path.relative_to(ROOT / "assets") == Path(*folders, f"{entity}.yml")


@pytest.mark.parametrize("path", CONTRACTS, ids=relative)
def test_domain_is_declared_outside_the_id(path):
    c = read(path)
    assert c["domain"], "o contrato precisa declarar o domínio"
    assert c["domain"] not in c["id"].split("."), "o domínio não faz parte do ID (data-platform/docs/assets.md)"


def test_unique_ids_and_existing_dependencies():
    contracts = [read(p) for p in CONTRACTS]
    ids = [c["id"] for c in contracts]
    assert len(ids) == len(set(ids)), "ID de asset repetido"
    for c in contracts:
        deps = next(p["value"] for p in c["customProperties"] if p["property"] == "depends_on")
        assert set(deps) <= set(ids), f"{c['id']} depende de asset sem contrato: {set(deps) - set(ids)}"


def test_every_asset_has_a_module_in_the_lib():
    for c in (read(p) for p in CONTRACTS):
        *folders, entity = c["id"].split(".")
        module = importlib.import_module("labdata.assets." + ".".join(folders))
        assert getattr(module, entity).id == c["id"]
