"""Portas: o que o sdk precisa do mundo externo, sem saber quem implementa.

Os adaptadores (sdk/adapters) implementam estas interfaces para a AWS; os testes usam versões em memória.
"""

from __future__ import annotations

from typing import Protocol


class ObjectStore(Protocol):
    """Armazenamento de objetos (S3 na AWS)."""

    def put(self, key: str, content: bytes, content_type: str = "application/json") -> None: ...

    def get(self, key: str) -> bytes: ...

    def list(self, prefix: str) -> list[str]: ...

    def delete(self, keys: list[str]) -> None: ...

    def uri(self, key: str) -> str: ...


class HttpClient(Protocol):
    """Cliente HTTP. Devolve o status e o corpo, para a fonte decidir o que um 404 significa."""

    def get(self, url: str) -> tuple[int, bytes]: ...
