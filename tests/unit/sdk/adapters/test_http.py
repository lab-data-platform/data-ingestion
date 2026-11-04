"""Cliente HTTP: devolve 4xx para a fonte decidir; tenta de novo em 5xx e erro de rede."""

import io
import urllib.error

import pytest

from labdata.sdk.adapters.http.client import UrllibClient
from labdata.sdk.core import SourceUnavailable


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "erro", {}, io.BytesIO(b"body"))


def test_200(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: Response(b"[]"))
    assert UrllibClient().get("https://x") == (200, b"[]")


def test_404_returns_without_retry(monkeypatch):
    calls = []

    def urlopen(*a, **k):
        calls.append(1)
        raise http_error(404)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    assert UrllibClient().get("https://x") == (404, b"body")
    assert len(calls) == 1


def test_5xx_retries_and_gives_up(monkeypatch):
    calls = []

    def urlopen(*a, **k):
        calls.append(1)
        raise http_error(503)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(SourceUnavailable):
        UrllibClient(attempts=3).get("https://x")
    assert len(calls) == 3
