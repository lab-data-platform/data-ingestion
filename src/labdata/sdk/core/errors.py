"""Erros da plataforma. A state machine decide o que fazer pelo nome do erro."""


class LabdataError(Exception):
    """Base de todos os erros da plataforma."""


class SourceUnavailable(LabdataError):
    """A fonte não respondeu, mesmo depois das tentativas. A state machine tenta de novo e, se persistir, alerta."""


class NoData(LabdataError):
    """A fonte não tem dado para a data pedida (ex.: feriado). A execução termina com sucesso, sem gravar."""


class ValidationFailed(LabdataError):
    """O dado não cumpre o contrato. Vai para a quarentena, com o motivo."""

    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


class ContractNotFound(LabdataError):
    """O asset pedido não tem contrato em assets/."""
