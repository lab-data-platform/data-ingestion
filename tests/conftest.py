"""Peças compartilhadas pelos testes: armazenamento em memória, API falsa e caminhos do repositório."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from labdata.sdk.core.models import RunContext

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMAS = ROOT / "schemas"


class InMemoryStore:
    """ObjectStore em memória, para testar o sdk sem S3."""

    def __init__(self, bucket: str = "bucket-teste"):
        self.bucket = bucket
        self.objects: dict[str, bytes] = {}

    def put(self, key, content, content_type="application/json"):
        self.objects[key] = content

    def get(self, key):
        return self.objects[key]

    def list(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))

    def delete(self, keys):
        for k in keys:
            self.objects.pop(k, None)

    def uri(self, key):
        return f"s3://{self.bucket}/{key}"


class FakeHttp:
    """Cliente HTTP que devolve respostas pré-definidas e guarda as URLs pedidas."""

    def __init__(self, status: int, body: bytes):
        self.status, self.body = status, body
        self.urls: list[str] = []

    def get(self, url):
        self.urls.append(url)
        return self.status, self.body


def fixture_bytes(*parts: str) -> bytes:
    return FIXTURES.joinpath(*parts).read_bytes()


def load_schema(*parts: str) -> dict:
    return json.loads(SCHEMAS.joinpath(*parts).read_text(encoding="utf-8"))


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def run() -> RunContext:
    return RunContext(
        run_id="arn:aws:states:us-east-2:123456789012:execution:teste:1",
        pipeline="bcb/sgs/cdi_diario",
        started_at=datetime(2026, 11, 3, 13, 0, tzinfo=UTC),
    )
