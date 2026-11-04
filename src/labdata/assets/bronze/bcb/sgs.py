"""Assets do bronze produzidos a partir do Banco Central."""

from labdata.sdk.governance.contracts.assets import load_asset as asset

cdi_diario = asset("bronze.bcb.sgs.cdi_diario")
