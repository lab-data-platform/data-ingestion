"""Emite os eventos OpenLineage de cada execução (START, COMPLETE, FAIL).

Destino definido pelo ambiente, como no cliente oficial:
- `OPENLINEAGE_URL` definido (ex.: Marquez local): envia por HTTP;
- `OPENLINEAGE_DISABLED=true`: não emite;
- nenhum dos dois: escreve o evento no log (console), que é o padrão do cliente.
Falha ao emitir linhagem nunca derruba a ingestão: o erro vai para o log.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import InputDataset, Job, OutputDataset, Run, RunEvent, RunState

from labdata.sdk.core.models import RunContext

log = logging.getLogger(__name__)

PRODUCER = "https://github.com/lab-data-platform/data-ingestion"
JOB_NAMESPACE = "lab-data"


class Lineage:
    def __init__(
        self,
        *,
        run: RunContext,
        input_namespace: str,
        input_name: str,
        output_namespace: str,
        output_name: str,
        client: OpenLineageClient | None = None,
    ):
        self.run = run
        self.inputs = [InputDataset(namespace=input_namespace, name=input_name)]
        self.outputs = [OutputDataset(namespace=output_namespace, name=output_name)]
        self._client = client

    @property
    def client(self) -> OpenLineageClient:
        if self._client is None:
            self._client = OpenLineageClient()
        return self._client

    def _emit(self, state: RunState) -> None:
        event = RunEvent(
            eventType=state,
            eventTime=datetime.now(UTC).isoformat(),
            run=Run(runId=_run_uuid(self.run.run_id)),
            job=Job(namespace=JOB_NAMESPACE, name=self.run.pipeline),
            producer=PRODUCER,
            inputs=self.inputs,
            outputs=self.outputs,
        )
        try:
            self.client.emit(event)
        except Exception:  # linhagem não pode derrubar a ingestão
            log.exception("falha ao emitir evento OpenLineage %s", state)

    def start(self) -> None:
        self._emit(RunState.START)

    def complete(self) -> None:
        self._emit(RunState.COMPLETE)

    def fail(self) -> None:
        self._emit(RunState.FAIL)


def _run_uuid(run_id: str) -> str:
    """O OpenLineage exige um UUID; deriva um UUID estável do run_id (ARN da execução ou request id)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, run_id))
