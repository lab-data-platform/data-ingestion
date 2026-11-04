"""O que é comum a toda extração do Banco Central (SGS).

Comportamento da API, estudado em 2026-11-02:
- séries diárias exigem janela (dataInicial/dataFinal) de no máximo 10 anos;
- dataInicial = dataFinal é recusado (HTTP 400): a janela precisa ter pelo menos dois dias;
- sem dado na janela (fim de semana, feriado, dia ainda não publicado): HTTP 404 "Value(s) not found";
- série inexistente: a conexão fica pendurada até o timeout.
"""

from __future__ import annotations

import os
from datetime import date

#: Pode ser trocada no ambiente local, para apontar para um servidor de fixtures.
BASE_URL = os.environ.get("BCB_SGS_BASE_URL", "https://api.bcb.gov.br/dados/serie")

#: Namespace OpenLineage das fontes do BCB.
LINEAGE_NAMESPACE = "https://api.bcb.gov.br"


def to_api_date(d: date) -> str:
    """Data no formato da API (dd/mm/aaaa)."""
    return d.strftime("%d/%m/%Y")


def series_url(series: int, start: date, end: date) -> str:
    query = f"formato=json&dataInicial={to_api_date(start)}&dataFinal={to_api_date(end)}"
    return f"{BASE_URL}/bcdata.sgs.{series}/dados?{query}"


def series_lineage_name(series: int) -> str:
    return f"/dados/serie/bcdata.sgs.{series}"
