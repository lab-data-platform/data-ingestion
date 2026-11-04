"""Layout e gravação do bronze: uma partição por data de referência, substituída a cada execução."""

import json
from datetime import date

from labdata.sdk.core import RawFile
from labdata.sdk.governance.contracts.assets import load_asset
from labdata.sdk.layers.bronze import BronzeLayout, BronzeWriter

ASSET = load_asset("bronze.bcb.sgs.cdi_diario")
D = date(2026, 10, 29)
PREFIX = "bcb/sgs/cdi_diario/reference_date=2026-10-29/"


def raw_file(value="0.050788"):
    records = [{"data": "29/10/2026", "valor": value}]
    return RawFile(name="data.json", content=json.dumps(records).encode(), records=records, source_uri="https://api")


def write(store, run, files):
    BronzeWriter(store).write(
        layout=BronzeLayout(ASSET),
        reference_date=D,
        files=files,
        run=run,
        source_asset_id="source.bcb.sgs.cdi_diario",
        request_params={"series": 12},
    )


def test_paths_derived_from_the_asset():
    layout = BronzeLayout(ASSET)
    assert layout.partition_prefix(D) == PREFIX
    assert layout.quarantine_prefix(D) == "_quarantine/" + PREFIX
    assert layout.manifest_key(D) == PREFIX + "_manifest.json"


def test_writes_data_and_manifest_with_technical_columns(store, run):
    write(store, run, [raw_file()])
    assert store.list(PREFIX) == [PREFIX + "_manifest.json", PREFIX + "data.json"]
    m = json.loads(store.get(PREFIX + "_manifest.json"))
    assert m["_run_id"] == run.run_id
    assert m["_source"] == "source.bcb.sgs.cdi_diario"
    assert m["_partition"] == "reference_date=2026-10-29"
    assert m["files"][0]["_source_file"] == f"s3://bucket-teste/{PREFIX}data.json"
    assert m["stats"]["records"] == 1


def test_rerunning_the_same_day_replaces_without_duplicating(store, run):
    store.put(PREFIX + "old-leftover.json", b"{}")
    for value in ("0.1", "0.2"):
        write(store, run, [raw_file(value)])
    keys = store.list("bcb/sgs/cdi_diario/")
    assert len(keys) == 2  # data.json + _manifest.json, sem a sobra
    assert json.loads(store.get(PREFIX + "data.json"))[0]["valor"] == "0.2"
