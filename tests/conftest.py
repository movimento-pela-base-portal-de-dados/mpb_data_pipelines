import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import boto3
import pytest
from moto import mock_aws
from prefect.testing.utilities import prefect_test_harness

BUCKET = "mpb-test"


@pytest.fixture(autouse=True, scope="session")
def prefect_backend():
    with prefect_test_harness():
        yield


@pytest.fixture
def bucket() -> str:
    return BUCKET


@pytest.fixture
def s3(monkeypatch, bucket):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("MPB_S3_BUCKET", bucket)
    with mock_aws():
        client = boto3.client("s3")
        client.create_bucket(Bucket=bucket)
        yield client


@pytest.fixture
def http_server():
    """Servidor HTTP local; `http_server(nome, conteudo)` publica um arquivo e retorna a URL."""
    files: dict[str, bytes] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            content = files.get(self.path.lstrip("/"))
            self.send_response(200 if content is not None else 404)
            self.end_headers()
            self.wfile.write(content or b"")

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def publish(name: str, content: bytes) -> str:
        files[name] = content
        return f"http://127.0.0.1:{server.server_port}/{name}"

    yield publish
    server.shutdown()
    server.server_close()
