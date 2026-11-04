"""Extrator genérico de uma série do SGS (Sistema Gerenciador de Séries Temporais do BCB).

Uma série = uma pipeline = um par de contratos (source e bronze). A série vem do arquivo da pipeline:

    extractor:
      class: labdata.extractors.bcb.sgs:Sgs
      params: {series: 12, asset_id: bronze.bcb.sgs.cdi_diario, source_asset_id: source.bcb.sgs.cdi_diario}

Regra de extração: pede a janela D → D+1 (a API recusa D → D) e grava só a observação de D.
Assim cada partição tem só o dado do próprio dia, e nunca há duplicação entre partições.
"""

from __future__ import annotations

import json
from datetime import timedelta

from labdata.extractors.bcb import client as bcb
from labdata.sdk.adapters.http.client import UrllibClient
from labdata.sdk.core.errors import NoData, SourceUnavailable
from labdata.sdk.core.extractor import Extractor
from labdata.sdk.core.models import ExtractRequest, RawFile
from labdata.sdk.core.ports import HttpClient

DATA_FILE = "data.json"


class Sgs(Extractor):
    def __init__(self, *, series: int, asset_id: str, source_asset_id: str, http: HttpClient | None = None):
        self.series = series
        self.asset_id = asset_id
        self.source_asset_id = source_asset_id
        self.http = http or UrllibClient()
        self.lineage_namespace = bcb.LINEAGE_NAMESPACE
        self.lineage_name = bcb.series_lineage_name(series)

    def extract(self, request: ExtractRequest) -> list[RawFile]:
        d = request.reference_date
        url = bcb.series_url(self.series, d, d + timedelta(days=1))
        status, body = self.http.get(url)

        if status == 404:
            raise NoData(
                f"SGS {self.series}: sem observação em {d.isoformat()} (fim de semana, feriado ou não publicado)"
            )
        if status != 200:
            raise SourceUnavailable(f"SGS {self.series}: HTTP {status} em {url}: {body[:200]!r}")

        observations = json.loads(body)
        of_the_day = [o for o in observations if o.get("data") == bcb.to_api_date(d)]
        if not of_the_day:
            raise NoData(f"SGS {self.series}: a janela não trouxe observação de {d.isoformat()}")

        content = json.dumps(of_the_day, ensure_ascii=False).encode("utf-8")
        return [RawFile(name=DATA_FILE, content=content, records=of_the_day, source_uri=url)]
