"""Extrai as pesquisas da planilha do observatório para um CSV e baixa os arquivos.

Lê as abas `2023`, `2024` e `2025-2026` (veja `ABAS` em `constants.py`; a aba `Metadados` é
ignorada) e grava uma linha por pesquisa com o valor bruto de cada célula: este script não trata
nem normaliza os valores. A conversão para o schema `pesquisa` do CKAN é feita pelo
`publicar_ckan.py`, que lê este CSV.

Também baixa os arquivos das colunas de recurso (`Link acesso`, `Relatório`, `Sumário`,
`Ficha site`), pelo hiperlink da célula ou pelo texto, se ele for uma URL. Os links do SharePoint
são baixados com o Playwright: o script faz o login da Microsoft com `SHAREPOINT_USER` e
`SHAREPOINT_PASSWORD` do `.env` e guarda a sessão em `.sharepoint_state.json`. Na primeira vez,
instale o navegador com `uv run playwright install chromium`.

Uso:

    uv run python -m scripts.extrair_pesquisas [--planilha PATH] [--saida-dir DIR]
        [--sem-download] [--sharepoint-visivel]

Saída (em `--saida-dir`, padrão `output/`):

    pesquisas.csv                           uma pesquisa por linha
    arquivos/<aba>/<linha>/<tipo>/<arq>     arquivo baixado de cada recurso

Colunas do CSV:

- `aba`, `linha`: de onde veio a pesquisa.
- as colunas da planilha, na mesma ordem, com o cabeçalho e o valor como estão na planilha
  (o cabeçalho `Resumo` aparece duas vezes, como na planilha).
- `recurso.<tipo>.links`, `.status`, `.caminho_arquivo` e `.erro` para cada `tipo_documento`.
  `caminho_arquivo` é relativo a `--saida-dir` e fica vazio se o download não ocorreu.
"""

import argparse
import contextlib
import csv
import os
import re
import sys
import time
import warnings
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from email.message import Message
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import httpx
import openpyxl
from dotenv import load_dotenv
from openpyxl.cell import Cell
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from .constants import (
    ABAS,
    ARQUIVOS_SUBDIR,
    COL_TITULO,
    COLUNAS_FORMATO,
    COLUNAS_LINK,
    CSV_CAMPO_CAMINHO_ARQUIVO,
    CSV_CAMPOS_RECURSO,
    CSV_COLUNA_ABA,
    CSV_COLUNA_LINHA,
    CSV_ENCODING,
    CSV_NOME,
    CSV_PREFIXO_RECURSO,
    CSV_SEPARADOR_LISTA,
    DEFAULT_PLANILHA,
    DEFAULT_SAIDA_DIR,
    DOWNLOAD_CHUNK_BYTES,
    DOWNLOAD_ERRO,
    DOWNLOAD_MAX_BYTES,
    DOWNLOAD_NAO_DIVULGAR,
    DOWNLOAD_NAO_E_ARQUIVO,
    DOWNLOAD_OK,
    DOWNLOAD_PULADO,
    DOWNLOAD_REQUER_AUTENTICACAO,
    DOWNLOAD_SEM_LINK,
    DOWNLOAD_TIMEOUT_SECONDS,
    ENV_ARQUIVO,
    ENV_SHAREPOINT_SENHA,
    ENV_SHAREPOINT_USUARIO,
    EXTENSOES_ACEITAS,
    GOOGLE_DOCS_EXPORT_FORMATS,
    GOOGLE_DOCS_HOST,
    GOOGLE_DRIVE_DOWNLOAD_URL,
    GOOGLE_DRIVE_HOST,
    HOSTS_AUTENTICADOS,
    LINHA_CABECALHO,
    MARCAS_NAO_DIVULGAR,
    NOME_ARQUIVO_PADRAO,
    RE_SHAREPOINT_PREFIXO_REDIRECIONAMENTO,
    SELETOR_EMAIL,
    SELETOR_ENVIAR,
    SELETOR_MANTER_CONECTADO,
    SELETOR_SENHA,
    SHAREPOINT_DOWNLOAD_PATH,
    SHAREPOINT_ESPERA_PAGINA,
    SHAREPOINT_ESTADO,
    SHAREPOINT_ESTADO_PERMISSAO,
    SHAREPOINT_LAYOUTS,
    SHAREPOINT_LOGIN_INTERVALO_MS,
    SHAREPOINT_LOGIN_TIMEOUT_SECONDS,
    SHAREPOINT_PARAM_CAMINHO,
    SHAREPOINT_PARAM_DOCUMENTO,
    SHAREPOINT_PARAM_DOWNLOAD,
    SHAREPOINT_PASSO_TIMEOUT_MS,
    SHAREPOINT_SITE_URL,
    USER_AGENT,
)

# --------------------------------------------------------------------------------------------
# Leitura da planilha
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Coluna:
    letra: str
    cabecalho: str  # como está na planilha

    @property
    def nome(self) -> str:
        """Cabeçalho sem os espaços nas pontas, como nas constantes `COL_*`."""
        return self.cabecalho.strip()

    @property
    def tipo_documento(self) -> str | None:
        return COLUNAS_LINK.get(self.nome) or COLUNAS_FORMATO.get(self.nome)


def ler_colunas(cabecalhos: Iterable[Cell]) -> list[Coluna]:
    return [
        Coluna(cell.column_letter, str(cell.value)) for cell in cabecalhos if cell.value is not None
    ]


def vazia(valor: object) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def is_url(valor: object) -> bool:
    return isinstance(valor, str) and valor.strip().lower().startswith(("http://", "https://"))


def links_da_celula(cell: Cell) -> list[str]:
    """Destino do hiperlink primeiro, depois o texto (se for URL).

    Em algumas linhas o texto aponta para o SharePoint e o hiperlink para o PDF público.
    """
    candidatos = []
    if cell.hyperlink is not None and is_url(cell.hyperlink.target):
        candidatos.append(cell.hyperlink.target.strip())
    if is_url(cell.value):
        candidatos.append(cell.value.strip())
    return list(dict.fromkeys(candidatos))


def nao_divulgar(textos: Iterable[object]) -> bool:
    textos = [str(texto or "").lower() for texto in textos]
    return any(marca in texto for texto in textos for marca in MARCAS_NAO_DIVULGAR)


def recursos_da_linha(colunas: list[Coluna], cells: dict[str, Cell]) -> list[dict]:
    """Links de cada `tipo_documento` e se o arquivo pode ser divulgado."""
    recursos: dict[str, dict] = {}
    for coluna in colunas:
        if (tipo := coluna.tipo_documento) is None:
            continue
        cell = cells[coluna.letra]
        recurso = recursos.setdefault(tipo, {"tipo_documento": tipo, "links": [], "textos": []})
        recurso["textos"].append(cell.value)
        if coluna.nome in COLUNAS_LINK:
            recurso["links"] = links_da_celula(cell)
    return [
        {
            "tipo_documento": r["tipo_documento"],
            "links": r["links"],
            "divulgar": not nao_divulgar([*r["textos"], *r["links"]]),
        }
        for r in recursos.values()
    ]


def extrair(planilha: Path) -> tuple[list[Coluna], list[dict]]:
    with warnings.catch_warnings():
        # A planilha usa uma extensão de validação de dados que o openpyxl não lê.
        warnings.simplefilter("ignore", UserWarning)
        # `data_only` lê o valor calculado das fórmulas (VLOOKUP), não a fórmula.
        workbook = openpyxl.load_workbook(planilha, data_only=True)
    colunas: list[Coluna] = []
    pesquisas: list[dict] = []
    for aba in ABAS:
        sheet = workbook[aba]
        colunas_aba = ler_colunas(sheet[LINHA_CABECALHO])
        if not colunas:
            colunas = colunas_aba
        elif colunas_aba != colunas:
            raise ValueError(f"aba {aba!r}: cabeçalho diferente da aba {ABAS[0]!r}")
        titulo = next(c for c in colunas if c.nome == COL_TITULO)

        for row in sheet.iter_rows(min_row=LINHA_CABECALHO + 1):
            cells = {cell.column_letter: cell for cell in row}
            # Linhas sem título (a aba `2023` tem linhas vazias formatadas no fim) são puladas.
            if vazia(cells[titulo.letra].value):
                continue
            pesquisas.append(
                {
                    "aba": aba,
                    "linha": row[0].row,
                    "valores": [cells[c.letra].value for c in colunas],
                    "recursos": recursos_da_linha(colunas, cells),
                }
            )
    return colunas, pesquisas


# --------------------------------------------------------------------------------------------
# Download dos arquivos
# --------------------------------------------------------------------------------------------


@dataclass
class ResultadoDownload:
    status: str
    caminho: Path | None = None
    erro: str | None = None


class NaoEArquivo(Exception):
    pass


class LoginSharePointFalhou(Exception):
    pass


def urls_de_download(url: str) -> list[str]:
    """URLs a tentar, em ordem. Links de visualização do Google viram download direto."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not host.endswith((GOOGLE_DRIVE_HOST, GOOGLE_DOCS_HOST)):
        return [url]
    query = parse_qs(parsed.query)
    match = re.search(r"/d/([\w-]+)", parsed.path)
    file_id = match.group(1) if match else (query.get("id") or [None])[0]
    if not file_id:
        return [url]
    params = {"id": file_id, "export": "download", "confirm": "t"}
    if resource_key := (query.get("resourcekey") or [None])[0]:
        params["resourcekey"] = resource_key
    urls = [f"{GOOGLE_DRIVE_DOWNLOAD_URL}?{urlencode(params)}"]
    # Arquivo nativo do Google Docs: o download direto falha e só a exportação funciona.
    kind = PurePosixPath(parsed.path).parts[1:2]
    if host.endswith(GOOGLE_DOCS_HOST) and kind and kind[0] in GOOGLE_DOCS_EXPORT_FORMATS:
        export = GOOGLE_DOCS_EXPORT_FORMATS[kind[0]]
        urls.append(f"https://{GOOGLE_DOCS_HOST}/{kind[0]}/d/{file_id}/export?format={export}")
    return urls


def url_de_download_sharepoint(link: str) -> str:
    """URL de download direto de um link do SharePoint.

    - `.../Forms/AllItems.aspx?id=<caminho do arquivo>`: `download.aspx?SourceUrl=<caminho>`;
    - `.../_layouts/15/Doc.aspx?sourcedoc={<id>}` (Office Online): `download.aspx?UniqueId=<id>`;
    - link de compartilhamento (`/:w:/s/...`): o próprio link com `download=1`.
    """
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if documento := query.get(SHAREPOINT_PARAM_DOCUMENTO):
        caminho_site = re.sub(RE_SHAREPOINT_PREFIXO_REDIRECIONAMENTO, "", parsed.path)
        site = caminho_site.split(SHAREPOINT_LAYOUTS)[0]
        unique_id = documento[0].strip("{}")
        return f"{base}{site}{SHAREPOINT_DOWNLOAD_PATH}?{urlencode({'UniqueId': unique_id})}"
    if caminho := query.get(SHAREPOINT_PARAM_CAMINHO):
        # `/sites/<site>/<biblioteca>/...`: o site são os dois primeiros segmentos.
        site = "/".join(caminho[0].split("/")[:3])
        params = urlencode({"SourceUrl": caminho[0]}, quote_via=quote)
        return f"{base}{site}{SHAREPOINT_DOWNLOAD_PATH}?{params}"
    return f"{link}{'&' if parsed.query else '?'}{SHAREPOINT_PARAM_DOWNLOAD}"


def _sanitizar_nome(nome: str) -> str:
    nome = PurePosixPath(nome.replace("\\", "/")).name
    nome = re.sub(r"[^\w.\- ()]", "_", nome).strip(" .")
    return nome or NOME_ARQUIVO_PADRAO


def _extensao(nome: str) -> str:
    return PurePosixPath(nome).suffix.lstrip(".").lower()


def _nome_do_arquivo(headers: Mapping[str, str], url_path: str, mimetype: str) -> str:
    if disposition := headers.get("content-disposition"):
        message = Message()
        message["content-disposition"] = disposition
        if filename := message.get_filename():
            # O SharePoint manda o nome com escape de URL (`Relat%C3%B3rio.pdf`).
            return _sanitizar_nome(unquote(filename))
    nome = _sanitizar_nome(unquote(PurePosixPath(url_path).name))
    if _extensao(nome) not in EXTENSOES_ACEITAS:
        extensao = next((e for e, m in EXTENSOES_ACEITAS.items() if m == mimetype), None)
        if extensao:
            nome = f"{nome}.{extensao}"
    return nome


def _validar(headers: Mapping[str, str], url_path: str) -> str:
    """Nome do arquivo, ou `NaoEArquivo` se a resposta for uma página (login, visualizador)."""
    mimetype = headers.get("content-type", "").split(";")[0].strip().lower()
    nome = _nome_do_arquivo(headers, url_path, mimetype)
    # O `clean.py` tira o formato e o mimetype do recurso da extensão do arquivo.
    if mimetype.startswith("text/html") or _extensao(nome) not in EXTENSOES_ACEITAS:
        raise NaoEArquivo(f"conteúdo {mimetype or 'desconhecido'} ({nome})")
    return nome


def _gravar(destino: Path, nome: str, chunks: Iterable[bytes]) -> ResultadoDownload:
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / nome
    tamanho = 0
    try:
        with caminho.open("wb") as fh:
            for chunk in chunks:
                tamanho += len(chunk)
                if tamanho > DOWNLOAD_MAX_BYTES:
                    raise ValueError(f"arquivo maior que {DOWNLOAD_MAX_BYTES} bytes")
                fh.write(chunk)
    except BaseException:
        caminho.unlink(missing_ok=True)
        raise
    return ResultadoDownload(status=DOWNLOAD_OK, caminho=caminho)


def _baixar(client: httpx.Client, url: str, destino: Path) -> ResultadoDownload:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        nome = _validar(response.headers, response.url.path)
        return _gravar(destino, nome, response.iter_bytes(DOWNLOAD_CHUNK_BYTES))


class SharePoint:
    """Sessão do Playwright logada no SharePoint com o usuário e a senha do `.env`.

    Abre o site, preenche o login da Microsoft e guarda os cookies em `SHAREPOINT_ESTADO`, que
    são reaproveitados nas próximas execuções. Os arquivos são baixados com esses cookies
    (`context.request`), sem abrir o visualizador do Office. Se a conta pedir MFA, rode com
    `--sharepoint-visivel` e conclua a verificação na janela do navegador.
    """

    def __init__(self, usuario: str, senha: str, visivel: bool = False):
        self._usuario = usuario
        self._senha = senha
        self._visivel = visivel

    def __enter__(self) -> "SharePoint":
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=not self._visivel)
            estado = SHAREPOINT_ESTADO if SHAREPOINT_ESTADO.exists() else None
            self._context = self._browser.new_context(storage_state=estado)
            self._entrar()
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self, *_exc: object) -> None:
        if browser := getattr(self, "_browser", None):
            browser.close()
        self._playwright.stop()

    def _entrar(self) -> None:
        page = self._context.new_page()
        page.set_default_timeout(SHAREPOINT_PASSO_TIMEOUT_MS)
        # Basta o HTML: o evento `load` do SharePoint moderno pode passar de 30 s.
        page.goto(SHAREPOINT_SITE_URL, wait_until=SHAREPOINT_ESPERA_PAGINA)
        if not self._logado(page):
            page.locator(SELETOR_EMAIL).fill(self._usuario)
            page.locator(SELETOR_ENVIAR).first.click()
            page.locator(SELETOR_SENHA).fill(self._senha)
            page.locator(SELETOR_ENVIAR).first.click()
            # Até chegar ao SharePoint: responde ao "Continuar conectado?" e espera o MFA.
            prazo = time.monotonic() + SHAREPOINT_LOGIN_TIMEOUT_SECONDS
            while not self._logado(page):
                if time.monotonic() > prazo:
                    raise LoginSharePointFalhou(
                        f"login não concluído em {SHAREPOINT_LOGIN_TIMEOUT_SECONDS}s ({page.url});"
                        " se a conta pede MFA, rode com --sharepoint-visivel"
                    )
                if page.locator(SELETOR_MANTER_CONECTADO).count():
                    page.locator(SELETOR_ENVIAR).first.click()
                page.wait_for_timeout(SHAREPOINT_LOGIN_INTERVALO_MS)
        self._context.storage_state(path=SHAREPOINT_ESTADO)
        SHAREPOINT_ESTADO.chmod(SHAREPOINT_ESTADO_PERMISSAO)  # só o dono lê os cookies
        page.close()

    @staticmethod
    def _logado(page: Page) -> bool:
        return page.url.startswith(SHAREPOINT_SITE_URL)

    def baixar(self, link: str, destino: Path) -> ResultadoDownload:
        url = url_de_download_sharepoint(link)
        response = self._context.request.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS * 1000)
        if not response.ok:
            return ResultadoDownload(
                status=DOWNLOAD_ERRO, erro=f"{url}: HTTP {response.status} {response.status_text}"
            )
        nome = _validar(response.headers, urlparse(response.url).path)
        return _gravar(destino, nome, [response.body()])


def baixar_arquivo(
    client: httpx.Client, sharepoint: SharePoint | None, links: list[str], destino: Path
) -> ResultadoDownload:
    """Devolve o primeiro download bem-sucedido entre os links, ou o motivo da última falha."""
    falha = ResultadoDownload(status=DOWNLOAD_SEM_LINK)
    for link in links:
        if urlparse(link).netloc.lower().endswith(HOSTS_AUTENTICADOS):
            if sharepoint is None:
                falha = ResultadoDownload(status=DOWNLOAD_REQUER_AUTENTICACAO, erro=link)
                continue
            try:
                return sharepoint.baixar(link, destino)
            except NaoEArquivo as exc:
                falha = ResultadoDownload(status=DOWNLOAD_NAO_E_ARQUIVO, erro=f"{link}: {exc}")
            except (PlaywrightError, OSError, ValueError) as exc:
                falha = ResultadoDownload(status=DOWNLOAD_ERRO, erro=f"{link}: {exc}")
            continue
        for url in urls_de_download(link):
            try:
                return _baixar(client, url, destino)
            except NaoEArquivo as exc:
                falha = ResultadoDownload(status=DOWNLOAD_NAO_E_ARQUIVO, erro=f"{url}: {exc}")
            except (httpx.HTTPError, OSError, ValueError) as exc:
                falha = ResultadoDownload(status=DOWNLOAD_ERRO, erro=f"{url}: {exc}")
    return falha


def registrar_download(recurso: dict, resultado: ResultadoDownload, saida_dir: Path) -> None:
    recurso["status"] = resultado.status
    recurso["erro"] = resultado.erro
    recurso[CSV_CAMPO_CAMINHO_ARQUIVO] = (
        resultado.caminho.relative_to(saida_dir).as_posix() if resultado.caminho else None
    )


def sessao_sharepoint(pesquisas: list[dict], visivel: bool) -> SharePoint | None:
    """Sessão do SharePoint, se há links para lá e credenciais no `.env`."""
    links = (link for p in pesquisas for r in p["recursos"] if r["divulgar"] for link in r["links"])
    if not any(urlparse(link).netloc.lower().endswith(HOSTS_AUTENTICADOS) for link in links):
        return None
    usuario = os.environ.get(ENV_SHAREPOINT_USUARIO)
    senha = os.environ.get(ENV_SHAREPOINT_SENHA)
    if not (usuario and senha):
        print(
            f"aviso: defina {ENV_SHAREPOINT_USUARIO} e {ENV_SHAREPOINT_SENHA} no {ENV_ARQUIVO}"
            " para baixar os arquivos do SharePoint",
            file=sys.stderr,
        )
        return None
    return SharePoint(usuario, senha, visivel)


def baixar_arquivos(pesquisas: list[dict], saida_dir: Path, sharepoint_visivel: bool) -> None:
    client = httpx.Client(
        follow_redirects=True,
        timeout=DOWNLOAD_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )
    sharepoint = sessao_sharepoint(pesquisas, sharepoint_visivel)
    with client, sharepoint or contextlib.nullcontext():
        for i, pesquisa in enumerate(pesquisas, start=1):
            for recurso in pesquisa["recursos"]:
                if recurso["divulgar"]:
                    destino = saida_dir / ARQUIVOS_SUBDIR / pesquisa["aba"]
                    destino /= str(pesquisa["linha"])
                    destino /= recurso["tipo_documento"]
                    resultado = baixar_arquivo(client, sharepoint, recurso["links"], destino)
                else:
                    resultado = ResultadoDownload(status=DOWNLOAD_NAO_DIVULGAR)
                registrar_download(recurso, resultado, saida_dir)
            status = ", ".join(
                f"{r['tipo_documento']}={r['status']}"
                for r in pesquisa["recursos"]
                if r["status"] != DOWNLOAD_SEM_LINK
            )
            origem = f"{pesquisa['aba']}:{pesquisa['linha']}"
            print(f"[{i}/{len(pesquisas)}] {origem}: {status or DOWNLOAD_SEM_LINK}")


# --------------------------------------------------------------------------------------------
# Escrita
# --------------------------------------------------------------------------------------------


def _celula_csv(valor: object) -> object:
    if isinstance(valor, list):
        return CSV_SEPARADOR_LISTA.join(str(v) for v in valor)
    return valor


def escrever_csv(caminho: Path, colunas: list[Coluna], pesquisas: list[dict]) -> None:
    """Uma pesquisa por linha: origem, valores brutos da planilha e status dos recursos.

    Usa `csv.writer` (e não `DictWriter`) porque a planilha tem cabeçalhos repetidos.
    """
    tipos = list(dict.fromkeys(c.tipo_documento for c in colunas if c.tipo_documento))
    cabecalho = [
        CSV_COLUNA_ABA,
        CSV_COLUNA_LINHA,
        *(c.cabecalho for c in colunas),
        *(f"{CSV_PREFIXO_RECURSO}{t}.{k}" for t in tipos for k in CSV_CAMPOS_RECURSO),
    ]
    with caminho.open("w", encoding=CSV_ENCODING, newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(cabecalho)
        for p in pesquisas:
            recursos = {r["tipo_documento"]: r for r in p["recursos"]}
            writer.writerow(
                [
                    p["aba"],
                    p["linha"],
                    *p["valores"],
                    *(_celula_csv(recursos[t].get(k)) for t in tipos for k in CSV_CAMPOS_RECURSO),
                ]
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--planilha", type=Path, default=DEFAULT_PLANILHA)
    parser.add_argument("--saida-dir", type=Path, default=DEFAULT_SAIDA_DIR)
    parser.add_argument("--sem-download", action="store_true", help="não baixa os arquivos")
    parser.add_argument(
        "--sharepoint-visivel",
        action="store_true",
        help="abre o navegador do login do SharePoint (para concluir o MFA à mão)",
    )
    args = parser.parse_args(argv)
    load_dotenv(ENV_ARQUIVO)

    colunas, pesquisas = extrair(args.planilha)
    args.saida_dir.mkdir(parents=True, exist_ok=True)
    if args.sem_download:
        for pesquisa in pesquisas:
            for recurso in pesquisa["recursos"]:
                registrar_download(
                    recurso, ResultadoDownload(status=DOWNLOAD_PULADO), args.saida_dir
                )
    else:
        baixar_arquivos(pesquisas, args.saida_dir, args.sharepoint_visivel)

    csv_path = args.saida_dir / CSV_NOME
    escrever_csv(csv_path, colunas, pesquisas)

    baixados = sum(r["status"] == DOWNLOAD_OK for p in pesquisas for r in p["recursos"])
    print(f"{len(pesquisas)} pesquisas, {baixados} arquivos baixados -> {csv_path}")


if __name__ == "__main__":
    main()
