"""Configuração da execução, vinda do ambiente e do arquivo da pipeline.

Variáveis de ambiente (preenchidas pelo Terraform a partir dos contratos do foundation e do lakehouse):
- LABDATA_PIPELINE: pipeline desta Lambda (ex.: "bcb/sgs/cdi_diario")
- LABDATA_ENV: ambiente (padrão "dev")
- BRONZE_BUCKET: bucket da camada bronze
- LABDATA_PIPELINES_DIR / LABDATA_ASSETS_DIR: opcionais, para apontar outra pasta (testes)
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from labdata.sdk.core.extractor import Extractor


@dataclass(frozen=True)
class PipelineConfig:
    pipeline: str
    asset: str
    extractor_class: str
    extractor_params: dict[str, Any] = field(default_factory=dict)
    reference_date_rule: str = "previous_business_day"
    timezone: str = "America/Sao_Paulo"

    def build_extractor(self) -> Extractor:
        module_name, class_name = self.extractor_class.split(":")
        cls = getattr(importlib.import_module(module_name), class_name)
        return cls(**self.extractor_params)


def pipelines_dir() -> Path:
    if env := os.environ.get("LABDATA_PIPELINES_DIR"):
        return Path(env)
    packaged = Path(__file__).resolve().parents[2] / "_pipelines"
    if packaged.is_dir():
        return packaged
    for parent in Path(__file__).resolve().parents:
        if (parent / "pipelines").is_dir() and (parent / "pyproject.toml").is_file():
            return parent / "pipelines"
    raise FileNotFoundError("pasta de pipelines não encontrada (defina LABDATA_PIPELINES_DIR)")


@cache
def load_pipeline(pipeline: str) -> PipelineConfig:
    data = yaml.safe_load((pipelines_dir() / f"{pipeline}.yml").read_text(encoding="utf-8"))
    if data["pipeline"] != pipeline:
        raise ValueError(f"o arquivo de {pipeline!r} declara pipeline={data['pipeline']!r}")
    schedule = data.get("schedule", {})
    return PipelineConfig(
        pipeline=data["pipeline"],
        asset=data["asset"],
        extractor_class=data["extractor"]["class"],
        extractor_params=data["extractor"].get("params", {}),
        reference_date_rule=schedule.get("reference_date", "previous_business_day"),
        timezone=schedule.get("timezone", "America/Sao_Paulo"),
    )


@dataclass(frozen=True)
class Environment:
    pipeline: str
    env: str
    bronze_bucket: str

    @classmethod
    def from_env(cls) -> Environment:
        return cls(
            pipeline=os.environ["LABDATA_PIPELINE"],
            env=os.environ.get("LABDATA_ENV", "dev"),
            bronze_bucket=os.environ["BRONZE_BUCKET"],
        )
