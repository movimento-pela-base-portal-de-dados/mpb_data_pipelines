from pathlib import Path

import pytest
from prefect import flow

from mpb_data_pipelines.s3 import Layer, build_s3_key, get_bucket, upload_file


def test_build_s3_key() -> None:
    key = build_s3_key(Layer.RAW, Path("dataset/tabela/dados.csv"))
    assert key == "raw/dataset/tabela/dados.csv"


@pytest.mark.parametrize("path", ["", "/tmp/dados.csv", "../dados.csv"])
def test_build_s3_key_rejects_non_relative_path(path: str) -> None:
    with pytest.raises(ValueError):
        build_s3_key(Layer.RAW, Path(path))


def test_get_bucket_requires_env(monkeypatch) -> None:
    monkeypatch.delenv("MPB_S3_BUCKET", raising=False)
    with pytest.raises(RuntimeError):
        get_bucket()


def test_upload_file(s3, bucket, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = Path("dataset/tabela/dados.csv")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"a,b\n1,2\n")

    @flow
    def run() -> str:
        return upload_file(Layer.PUBLISHED, path)

    key = "published/dataset/tabela/dados.csv"
    assert run() == f"s3://{bucket}/{key}"
    obj = s3.get_object(Bucket=bucket, Key=key)
    assert obj["Body"].read() == b"a,b\n1,2\n"
    assert obj["ContentType"] == "text/csv"
