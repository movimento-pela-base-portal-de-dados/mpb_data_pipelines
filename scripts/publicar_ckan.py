"""Publica no CKAN as pesquisas do JSON gerado por `clean.py`.

Uso:

    uv run python -m scripts.publicar_ckan [--json PATH] [--limite N] [--dry-run]

Lê `CKAN_URL`, `CKAN_API_KEY` e `CKAN_OWNER_ORG` do `.env` na raiz do repositório. Variáveis já
definidas no ambiente têm precedência sobre o arquivo.

O JSON já está limpo e no schema `pesquisa` do CKAN; este script não altera os dados. Para cada
pesquisa:

- envia o objeto `dataset` (`package_create` ou, se já existir, `package_patch`), mais a
  organização (`owner_org`);
- envia cada recurso por upload (`resource_create` ou, se já existir um com o mesmo nome,
  `resource_patch`). `caminho_arquivo` é relativo ao diretório do JSON.

O script é idempotente: atualiza o conjunto de dados e os recursos se já existirem.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .constants import (
    CKAN_API_PATH,
    CKAN_NOT_FOUND_ERROR,
    CKAN_TIMEOUT_SECONDS,
    DEFAULT_SAIDA_DIR,
    ENV_ARQUIVO,
    ENV_CKAN_API_KEY,
    ENV_CKAN_OWNER_ORG,
    ENV_CKAN_URL,
    JSON_NOME,
    USER_AGENT,
)


class CKANError(Exception):
    def __init__(self, action: str, error: dict):
        self.error = error
        super().__init__(f"{action}: {error}")

    @property
    def not_found(self) -> bool:
        return self.error.get("__type") == CKAN_NOT_FOUND_ERROR


class CKANClient:
    def __init__(self, url: str, api_key: str):
        self._client = httpx.Client(
            base_url=url.rstrip("/") + CKAN_API_PATH,
            headers={"Authorization": api_key, "User-Agent": USER_AGENT},
            timeout=CKAN_TIMEOUT_SECONDS,
        )

    def close(self) -> None:
        self._client.close()

    def action(self, name: str, data: dict | None = None, upload: Path | None = None) -> dict:
        if upload is None:
            response = self._client.post(name, json=data or {})
        else:
            with upload.open("rb") as fh:
                response = self._client.post(
                    name, data=data or {}, files={"upload": (upload.name, fh)}
                )
        try:
            body = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        if not body.get("success"):
            raise CKANError(name, body.get("error") or {"message": response.text})
        return body["result"]


def publicar_dataset(ckan: CKANClient, dataset: dict) -> dict:
    try:
        ckan.action("package_show", {"id": dataset["name"]})
    except CKANError as exc:
        if not exc.not_found:
            raise
        return ckan.action("package_create", dataset)
    # `package_patch` preserva os recursos existentes.
    return ckan.action("package_patch", {"id": dataset["name"], **dataset})


def publicar_recurso(ckan: CKANClient, package: dict, recurso: dict, caminho: Path) -> dict:
    existente = next(
        (r for r in package.get("resources", []) if r.get("name") == recurso["name"]), None
    )
    if existente:
        return ckan.action("resource_patch", {"id": existente["id"], **recurso}, upload=caminho)
    return ckan.action("resource_create", {"package_id": package["id"], **recurso}, upload=caminho)


def main(argv: list[str] | None = None) -> None:
    load_dotenv(ENV_ARQUIVO)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, default=DEFAULT_SAIDA_DIR / JSON_NOME)
    parser.add_argument("--url", default=os.environ.get(ENV_CKAN_URL))
    parser.add_argument("--org", default=os.environ.get(ENV_CKAN_OWNER_ORG))
    parser.add_argument("--limite", type=int, help="publica só as N primeiras pesquisas")
    parser.add_argument("--dry-run", action="store_true", help="mostra o payload sem enviar")
    args = parser.parse_args(argv)

    # `caminho_arquivo` é relativo ao diretório do JSON.
    base_dir = args.json.parent
    pesquisas = json.loads(args.json.read_text(encoding="utf-8"))["pesquisas"]
    if args.limite:
        pesquisas = pesquisas[: args.limite]

    if args.dry_run:
        for pesquisa in pesquisas:
            print(json.dumps(pesquisa, ensure_ascii=False, indent=2))
        return

    api_key = os.environ.get(ENV_CKAN_API_KEY)
    if not (args.url and api_key and args.org):
        parser.error(
            f"defina {ENV_CKAN_URL}, {ENV_CKAN_API_KEY} e {ENV_CKAN_OWNER_ORG} no {ENV_ARQUIVO}"
        )

    ckan = CKANClient(args.url, api_key)
    falhas = 0
    try:
        for i, pesquisa in enumerate(pesquisas, start=1):
            dataset = pesquisa["dataset"]
            prefixo = (
                f"[{i}/{len(pesquisas)}] {pesquisa['aba']}:{pesquisa['linha']} {dataset['name']}"
            )
            try:
                package = publicar_dataset(ckan, {**dataset, "owner_org": args.org})
                for recurso in pesquisa["recursos"]:
                    campos = {k: v for k, v in recurso.items() if k != "caminho_arquivo"}
                    caminho = base_dir / recurso["caminho_arquivo"]
                    publicar_recurso(ckan, package, campos, caminho)
                arquivos = ", ".join(r["caminho_arquivo"] for r in pesquisa["recursos"])
                print(f"{prefixo}: ok ({arquivos or 'sem arquivo'})")
            except (CKANError, httpx.HTTPError, OSError) as exc:
                falhas += 1
                print(f"{prefixo}: ERRO {exc}", file=sys.stderr)
    finally:
        ckan.close()

    print(f"{len(pesquisas) - falhas} publicadas, {falhas} com erro")
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
