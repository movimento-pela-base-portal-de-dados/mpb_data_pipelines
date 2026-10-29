"""Flow genérico de referência: raw -> processed -> published.

Para uma nova fonte, copie este módulo para `flows/<fonte>.py` e ajuste a URL, o
dataset, a tabela e as transformações. Os arquivos locais ficam em
`<dataset>/<tabela>/`, relativo ao diretório de execução, e esse mesmo caminho é
usado como chave dentro de cada camada do S3.
"""

from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import httpx
import pandas as pd
from prefect import flow, task

import mpb_data_pipelines.s3 as s3


@task(retries=3, retry_delay_seconds=30)
def download_raw_file(
    url: str, folder: Path, filename: str | None = None, timeout: float = 60.0
) -> Path:
    """Baixa `url` para `<folder>/<filename>` e retorna o caminho local.

    Sem `filename`, usa o nome do arquivo na URL.
    """
    filename = filename or PurePosixPath(urlsplit(url).path).name
    if not filename:
        raise ValueError(f"Informe filename: a URL não termina em um nome de arquivo: {url}")
    path = folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with path.open("wb") as file:
            for chunk in response.iter_bytes():
                file.write(chunk)
    return path


@flow(name="exemplo")
def main(url: str) -> None:
    dataset = "br_ibge_ipca"
    table = "ipca15"
    folder = Path(dataset) / table

    # O arquivo bruto pode ser renomeado com `filename`
    raw_file = download_raw_file(url, folder)
    s3.upload_file(s3.Layer.RAW, raw_file)

    df = pd.read_csv(raw_file).assign(year=2026)

    processed_file_path = folder / "processed.csv"
    df.to_csv(processed_file_path, index=False)

    s3.upload_file(s3.Layer.PROCESSED, processed_file_path)
    # Arquivo pronto para uso em produção
    s3.upload_file(s3.Layer.PUBLISHED, processed_file_path)
