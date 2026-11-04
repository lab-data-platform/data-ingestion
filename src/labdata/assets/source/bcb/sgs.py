"""Fontes externas do Banco Central."""

from labdata.sdk.governance.contracts.assets import load_asset as asset

cdi_diario = asset("source.bcb.sgs.cdi_diario")
