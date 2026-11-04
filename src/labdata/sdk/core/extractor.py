"""Classe base de toda fonte: o fluxo é sempre o mesmo, só a extração muda."""

from __future__ import annotations

from abc import ABC, abstractmethod

from labdata.sdk.core.models import ExtractRequest, RawFile


class Extractor(ABC):
    """Molde de uma fonte.

    Uma fonte nova implementa só o `extract()`: buscar o dado e devolver os arquivos como vieram.
    Gravar no bronze, validar, mandar para a quarentena, emitir linhagem e montar o evento
    ficam com o sdk (`labdata.sdk.runtime.pipeline`).
    """

    #: ID do asset produzido, igual ao `id` do contrato ODCS (ex.: "bronze.bcb.sgs.cdi_diario").
    asset_id: str

    #: ID do asset de origem, usado na linhagem (ex.: "source.bcb.sgs.cdi_diario").
    source_asset_id: str

    @abstractmethod
    def extract(self, request: ExtractRequest) -> list[RawFile]:
        """Busca na fonte o dado da data de referência.

        Deve levantar `NoData` quando a fonte não tem dado para a data (ex.: feriado)
        e `SourceUnavailable` quando a fonte não responde.
        """
