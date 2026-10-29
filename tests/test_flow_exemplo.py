from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
from prefect import flow

from mpb_data_pipelines.flows.dataset_exemplo.flow import download_raw_file, main


def test_download_raw_file(http_server, tmp_path) -> None:
    url = http_server("dados.csv", b"a,b\n1,2\n")

    @flow
    def run(filename: str | None = None) -> Path:
        return download_raw_file(url, tmp_path / "dataset/tabela", filename)

    assert run().read_bytes() == b"a,b\n1,2\n"
    assert run("renomeado.csv") == tmp_path / "dataset/tabela/renomeado.csv"


def test_download_raw_file_requires_filename(tmp_path) -> None:
    @flow
    def run() -> Path:
        return download_raw_file.with_options(retries=0)("https://example.org/", tmp_path)

    with pytest.raises(ValueError):
        run()


def test_exemplo_uploads_all_layers(s3, bucket, http_server, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    main(url=http_server("ipca15.csv", b"mes,valor\n1,0.5\n"))

    def read(key: str) -> bytes:
        return s3.get_object(Bucket=bucket, Key=key)["Body"].read()

    assert read("raw/br_ibge_ipca/ipca15/ipca15.csv") == b"mes,valor\n1,0.5\n"
    processed = read("processed/br_ibge_ipca/ipca15/processed.csv")
    assert read("published/br_ibge_ipca/ipca15/processed.csv") == processed
    df = pd.read_csv(StringIO(processed.decode()))
    assert df.to_dict("records") == [{"mes": 1, "valor": 0.5, "year": 2026}]
