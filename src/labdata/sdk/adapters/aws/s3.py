"""ObjectStore sobre o Amazon S3. O endpoint vem do ambiente (AWS_ENDPOINT_URL), o que permite usar o moto."""

from __future__ import annotations

import os
from typing import Any


class S3Store:
    def __init__(self, bucket: str, client: Any | None = None):
        self.bucket = bucket
        if client is None:
            import boto3
            from botocore.config import Config

            # Com endpoint local (moto), o bucket vai no caminho: http://moto:5000/<bucket>/<chave>
            path_style = bool(os.environ.get("AWS_ENDPOINT_URL"))
            client = boto3.client("s3", config=Config(s3={"addressing_style": "path" if path_style else "auto"}))
        self.client = client

    def put(self, key: str, content: bytes, content_type: str = "application/json") -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def list(self, prefix: str) -> list[str]:
        keys: list[str] = []
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [o["Key"] for o in page.get("Contents", [])]
        return keys

    def delete(self, keys: list[str]) -> None:
        for i in range(0, len(keys), 1000):  # limite da API DeleteObjects
            batch = [{"Key": k} for k in keys[i : i + 1000]]
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": batch, "Quiet": True})

    def uri(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"
