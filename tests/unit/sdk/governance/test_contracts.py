"""Contratos ODCS, nomes físicos derivados do ID e lib de assets."""

import pytest

from labdata.sdk.core import ContractNotFound
from labdata.sdk.governance.contracts.assets import Asset, load_all, load_asset


def test_physical_names_derived_from_id():
    a = load_asset("bronze.bcb.sgs.cdi_diario")
    assert (a.layer, a.origin, a.levels, a.entity) == ("bronze", "bcb", ("sgs",), "cdi_diario")
    assert a.s3_prefix == "bcb/sgs/cdi_diario/"
    assert a.table == "bcb_sgs_cdi_diario"
    assert a.glue_database() == "lab_data_dev_bronze"
    assert a.uri == "labdata://bronze/bcb/sgs/cdi_diario"
    assert a.openlineage_name() == "bcb/sgs/cdi_diario"
    assert a.domain == "financeiro"  # o domínio vem do contrato, e não do ID


def new_asset(asset_id):
    return Asset(
        id=asset_id,
        version="1.0.0",
        status="active",
        domain="financeiro",
        team="t",
        description="",
        classification="public",
        criticality="medium",
        depends_on=(),
        trigger="all",
        produced_by={},
    )


@pytest.mark.parametrize(
    ("asset_id", "levels", "prefix", "table"),
    [
        ("bronze.ibge.populacao", (), "ibge/populacao/", "ibge_populacao"),
        ("bronze.bcb.sgs.cdi_diario", ("sgs",), "bcb/sgs/cdi_diario/", "bcb_sgs_cdi_diario"),
        ("bronze.cvm.fi.doc.inf_diario", ("fi", "doc"), "cvm/fi/doc/inf_diario/", "cvm_fi_doc_inf_diario"),
        ("bronze.a.b.c.d.e.f", ("b", "c", "d", "e"), "a/b/c/d/e/f/", "a_b_c_d_e_f"),
    ],
)
def test_any_depth_follows_the_same_rule(asset_id, levels, prefix, table):
    a = new_asset(asset_id)
    assert (a.levels, a.s3_prefix, a.table) == (levels, prefix, table)


@pytest.mark.parametrize(
    "asset_id", ["bronze.cdi", "bronze.a.b.c.d.e.f.g", "raw.bcb.sgs", "bronze.BCB.sgs", "bronze..sgs"]
)
def test_invalid_id_is_rejected(asset_id):
    with pytest.raises(ValueError, match="fora do padrão"):
        new_asset(asset_id)


def test_platform_extensions_read_from_contract():
    a = load_asset("bronze.bcb.sgs.cdi_diario")
    assert a.classification == "public"
    assert a.criticality == "medium"
    assert a.depends_on == ("source.bcb.sgs.cdi_diario",)
    assert a.trigger == "all"
    assert a.produced_by["tool"] == "lambda"
    assert a.freshness["value"] == 4


def test_missing_contract_is_an_error():
    with pytest.raises(ContractNotFound):
        load_asset("bronze.bcb.sgs.does_not_exist")


def test_assets_lib_exposes_the_contracts():
    from labdata.assets.bronze.bcb import sgs as bronze
    from labdata.assets.source.bcb import sgs as source

    assert bronze.cdi_diario.id == "bronze.bcb.sgs.cdi_diario"
    assert source.cdi_diario.id in bronze.cdi_diario.depends_on


def test_typo_in_the_lib_is_an_import_error():
    with pytest.raises(ImportError):
        from labdata.assets.bronze.bcb.sgs import cdi_diaro  # noqa: F401


def test_load_all_reads_every_contract():
    assert set(load_all()) == {"source.bcb.sgs.cdi_diario", "bronze.bcb.sgs.cdi_diario"}
