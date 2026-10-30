"""Envio de arquivos para o S3 do portal, seguindo as camadas de `docs/CONTRACTS.md`.

Um arquivo local em `<dataset>/<tabela>/<arquivo>` é gravado na chave
`<camada>/<dataset>/<tabela>/<arquivo>`. O bucket vem da variável de ambiente
`MPB_S3_BUCKET`. As credenciais AWS seguem a cadeia padrão do boto3 (IAM Role,
variáveis de ambiente ou perfil local).
"""

import mimetypes
import os
from enum import StrEnum
from pathlib import Path, PurePosixPath

import boto3
from prefect import get_run_logger, task
from prefect.cache_policies import NO_CACHE

BUCKET_ENV_VAR = "MPB_S3_BUCKET"


class Layer(StrEnum):
    RAW = "raw"
    PROCESSED = "processed"
    PUBLISHED = "published"


def get_bucket() -> str:
    bucket = os.environ.get(BUCKET_ENV_VAR)
    if not bucket:
        raise RuntimeError(f"Defina a variável de ambiente {BUCKET_ENV_VAR} com o bucket S3.")
    return bucket


def build_s3_key(layer: Layer, path: Path) -> str:
    """Prefixa o caminho relativo `path` com a camada: `<camada>/<path>`."""
    relative = PurePosixPath(path.as_posix())
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"Caminho deve ser relativo, como '<dataset>/<tabela>/<arquivo>': {path}")
    return f"{layer.value}/{relative}"


def s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


@task(retries=3, retry_delay_seconds=10, cache_policy=NO_CACHE)
def upload_file(
    layer: Layer,
    path: Path,
    bucket: str | None = None,
    content_type: str | None = None,
) -> str:
    """Envia o arquivo local `path` para `<camada>/<path>` e retorna a URI `s3://`."""
    bucket = bucket or get_bucket()
    key = build_s3_key(layer, path)
    content_type = content_type or mimetypes.guess_type(str(path))[0]
    extra_args = {"ContentType": content_type} if content_type else None
    boto3.client("s3").upload_file(str(path), bucket, key, ExtraArgs=extra_args)
    uri = s3_uri(bucket, key)
    get_run_logger().info("Enviado %s", uri)
    return uri
