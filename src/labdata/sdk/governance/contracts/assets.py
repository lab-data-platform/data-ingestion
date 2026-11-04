"""Carrega os contratos ODCS de assets/ e deriva os nomes físicos a partir do ID.

Padrão da plataforma (data-platform/docs/assets.md):
- ID: <camada>.<origem>[.<nível>...].<entidade>, um caminho de 2 a 6 partes depois da camada
  (ex.: bronze.bcb.sgs.cdi_diario, bronze.cvm.fi.doc.inf_diario). O domínio NÃO faz parte do ID:
  fica no campo `domain` do contrato, para poder ser corrigido sem renomear nada.
- prefixo no S3: <caminho>/                 (bcb/sgs/cdi_diario/)
- tabela no Glue: <caminho com _>           (bcb_sgs_cdi_diario, no database lab_data_<env>_<camada>)
- URI: labdata://<camada>/<caminho>
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from labdata.sdk.core.errors import ContractNotFound

LAYERS = ("source", "bronze", "silver", "gold", "dw", "dashboard")

#: camada + origem + de 0 a 4 níveis intermediários + entidade
ID_PATTERN = re.compile(r"^(" + "|".join(LAYERS) + r")(\.[a-z][a-z0-9_]*){2,6}$")


@dataclass(frozen=True)
class Asset:
    """Um asset da plataforma, lido do contrato ODCS."""

    id: str
    version: str
    status: str
    domain: str
    team: str
    description: str
    classification: str
    criticality: str
    depends_on: tuple[str, ...]
    trigger: str
    produced_by: dict[str, str]
    schema: tuple[dict[str, Any], ...] = ()
    quality: tuple[dict[str, Any], ...] = ()
    freshness: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not ID_PATTERN.match(self.id):
            raise ValueError(f"ID de asset fora do padrão <camada>.<origem>[.<nível>...].<entidade>: {self.id!r}")

    # --- Partes do ID ---------------------------------------------------------------------------------

    @property
    def layer(self) -> str:
        return self.id.split(".")[0]

    @property
    def path(self) -> tuple[str, ...]:
        """O caminho do asset, sem a camada: (origem, níveis..., entidade)."""
        return tuple(self.id.split(".")[1:])

    @property
    def origin(self) -> str:
        return self.path[0]

    @property
    def levels(self) -> tuple[str, ...]:
        """Os níveis entre a origem e a entidade (sistema, subsistema...). Pode ser vazio."""
        return self.path[1:-1]

    @property
    def entity(self) -> str:
        return self.path[-1]

    # --- Nomes físicos derivados do ID ----------------------------------------------------------------

    @property
    def s3_prefix(self) -> str:
        return "/".join(self.path) + "/"

    @property
    def table(self) -> str:
        return "_".join(self.path)

    def glue_database(self, platform: str = "lab-data", env: str = "dev") -> str:
        return f"{platform.replace('-', '_')}_{env}_{self.layer}"

    @property
    def uri(self) -> str:
        return "labdata://" + self.id.replace(".", "/")

    def openlineage_name(self) -> str:
        """Nome do dataset no OpenLineage (o namespace é o bucket da camada, definido em tempo de execução)."""
        return self.s3_prefix.rstrip("/")


def _custom(props: list[dict[str, Any]], name: str, default: Any = None) -> Any:
    for p in props or []:
        if p.get("property") == name:
            return p.get("value")
    return default


def asset_from_contract(contract: dict[str, Any]) -> Asset:
    """Converte um contrato ODCS (já lido do YAML) num Asset."""
    custom = contract.get("customProperties", [])
    schema = contract.get("schema") or [{}]
    freshness = next((s for s in contract.get("slaProperties", []) if s.get("property") == "freshness"), {})
    return Asset(
        id=contract["id"],
        version=contract["version"],
        status=contract.get("status", ""),
        domain=contract["domain"],
        team=contract["team"]["name"],
        description=(contract.get("description") or {}).get("purpose", ""),
        classification=_custom(custom, "classification"),
        criticality=_custom(custom, "criticality"),
        depends_on=tuple(_custom(custom, "depends_on", [])),
        trigger=_custom(custom, "trigger", "all"),
        produced_by=_custom(custom, "produced_by", {}),
        schema=tuple(schema[0].get("properties", [])),
        quality=tuple(schema[0].get("quality", [])),
        freshness=freshness,
    )


def contracts_dir() -> Path:
    """Onde estão os contratos.

    1. `LABDATA_ASSETS_DIR`, se definido.
    2. Dentro do pacote (`labdata/assets/_contracts`), como no zip da Lambda e na instalação via Git.
    3. A pasta `assets/` na raiz do repositório, no desenvolvimento.
    """
    if env := os.environ.get("LABDATA_ASSETS_DIR"):
        return Path(env)
    packaged = Path(__file__).resolve().parents[3] / "assets" / "_contracts"
    if packaged.is_dir():
        return packaged
    for parent in Path(__file__).resolve().parents:
        if (parent / "assets").is_dir() and (parent / "pyproject.toml").is_file():
            return parent / "assets"
    raise ContractNotFound("pasta de contratos não encontrada (defina LABDATA_ASSETS_DIR)")


def contract_path(asset_id: str, base: Path | None = None) -> Path:
    """assets/<camada>/<origem>/<níveis...>/<entidade>.yml: o caminho do arquivo é o próprio ID."""
    *folders, entity = asset_id.split(".")
    return (base or contracts_dir()).joinpath(*folders, f"{entity}.yml")


@cache
def load_asset(asset_id: str) -> Asset:
    """Lê o contrato de um asset pelo ID. Erro se o contrato não existir ou não bater com o ID."""
    path = contract_path(asset_id)
    if not path.is_file():
        raise ContractNotFound(f"sem contrato para {asset_id!r} em {path}")
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if contract.get("id") != asset_id:
        raise ContractNotFound(f"o contrato em {path} declara id={contract.get('id')!r}, esperado {asset_id!r}")
    return asset_from_contract(contract)


def load_all(base: Path | None = None) -> dict[str, Asset]:
    """Lê todos os contratos da pasta, indexados pelo ID."""
    root = base or contracts_dir()
    assets: dict[str, Asset] = {}
    for path in sorted(root.rglob("*.yml")):
        asset = asset_from_contract(yaml.safe_load(path.read_text(encoding="utf-8")))
        assets[asset.id] = asset
    return assets
