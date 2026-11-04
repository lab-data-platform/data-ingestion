"""Testes da Lambda do CDI, sem rede e sem AWS: a API e o S3 são simulados.

Rodar: make test
"""

import io
import json
import os
import unittest
import urllib.error
from datetime import date
from unittest import mock

import handler

# Resposta real da API para a janela 29/10 → 30/10/2026: vêm os dois dias.
API_RESPONSE = [
    {"data": "29/10/2026", "valor": "0.050788"},
    {"data": "30/10/2026", "valor": "0.050788"},
]


def fake_response(rows):
    return io.BytesIO(json.dumps(rows).encode())


def http_error(code):
    return urllib.error.HTTPError("https://api.bcb.gov.br", code, "erro", {}, io.BytesIO(b""))


class TestPreviousBusinessDay(unittest.TestCase):
    def test_tuesday_returns_monday(self):
        self.assertEqual(handler.previous_business_day(date(2026, 11, 3)), date(2026, 11, 2))

    def test_monday_returns_friday(self):
        self.assertEqual(handler.previous_business_day(date(2026, 11, 2)), date(2026, 10, 30))


class TestFetch(unittest.TestCase):
    @mock.patch("urllib.request.urlopen", return_value=fake_response(API_RESPONSE))
    def test_asks_d_to_d_plus_1_and_keeps_only_d(self, urlopen):
        rows = handler.fetch(date(2026, 10, 29))

        self.assertEqual(rows, [{"data": "29/10/2026", "valor": "0.050788"}])
        url = urlopen.call_args.args[0]
        self.assertIn("dataInicial=29/10/2026&dataFinal=30/10/2026", url)

    @mock.patch("urllib.request.urlopen", side_effect=http_error(404))
    def test_404_means_no_data(self, _):
        self.assertEqual(handler.fetch(date(2026, 10, 31)), [])

    @mock.patch("urllib.request.urlopen", side_effect=http_error(500))
    def test_other_errors_fail_the_lambda(self, _):
        with self.assertRaises(urllib.error.HTTPError):
            handler.fetch(date(2026, 10, 29))


@mock.patch.dict(os.environ, {"BRONZE_BUCKET": "bucket-teste"})
class TestHandler(unittest.TestCase):
    @mock.patch("handler.boto3")
    @mock.patch("urllib.request.urlopen", return_value=fake_response(API_RESPONSE))
    def test_writes_the_partition_of_the_day(self, _, boto3):
        result = handler.handler({"reference_date": "2026-10-29"}, None)

        self.assertEqual(result["status"], "ok")
        put = boto3.client.return_value.put_object.call_args.kwargs
        self.assertEqual(put["Bucket"], "bucket-teste")
        self.assertEqual(put["Key"], "bcb/sgs/cdi_diario/reference_date=2026-10-29/data.jsonl")
        self.assertEqual(put["Body"], b'{"data": "29/10/2026", "valor": "0.050788"}\n')

    @mock.patch("handler.boto3")
    @mock.patch("urllib.request.urlopen", side_effect=http_error(404))
    def test_no_data_writes_nothing(self, _, boto3):
        result = handler.handler({"reference_date": "2026-10-31"}, None)

        self.assertEqual(result["status"], "no_data")
        boto3.client.return_value.put_object.assert_not_called()

    @mock.patch("handler.boto3")
    @mock.patch("urllib.request.urlopen", side_effect=http_error(404))
    @mock.patch("handler.previous_business_day", return_value=date(2026, 10, 30))
    def test_empty_event_uses_previous_business_day(self, *_):
        result = handler.handler({}, None)

        self.assertEqual(result["reference_date"], "2026-10-30")


if __name__ == "__main__":
    unittest.main()
