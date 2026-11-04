"""Cliente HTTP com timeout e retry, usando só a biblioteca padrão.

Devolve (status, corpo) para respostas HTTP, inclusive 4xx: a fonte decide o que um 404 significa.
Só erros de rede e 5xx são tentados de novo; esgotadas as tentativas, levanta `SourceUnavailable`.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request

from labdata.sdk.core.errors import SourceUnavailable

log = logging.getLogger(__name__)

USER_AGENT = "lab-data-ingestion/0.1 (+https://github.com/lab-data-platform/data-ingestion)"


class UrllibClient:
    def __init__(self, *, timeout_s: float = 15, attempts: int = 3, wait_s: float = 2, backoff_rate: float = 2):
        self.timeout_s = timeout_s
        self.attempts = attempts
        self.wait_s = wait_s
        self.backoff_rate = backoff_rate

    def get(self, url: str) -> tuple[int, bytes]:
        wait = self.wait_s
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
                    return resp.status, resp.read()
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    return e.code, e.read()
                last_error = e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_error = e
            log.warning("tentativa %d/%d falhou para %s: %s", attempt, self.attempts, url, last_error)
            if attempt < self.attempts:
                time.sleep(wait)
                wait *= self.backoff_rate
        raise SourceUnavailable(f"sem resposta de {url} após {self.attempts} tentativas: {last_error}")
