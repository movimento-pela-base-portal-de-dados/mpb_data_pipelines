"""Limpa e normaliza as pesquisas do CSV e gera o JSON que o `publicar_ckan.py` envia ao CKAN.

Uso:

    uv run python -m scripts.clean

Lê `output/pesquisas.csv` (valores brutos da planilha, gerado por `extrair_pesquisas.py`) e grava
`output/pesquisas.json`:

    {
      "fonte": "pesquisas.csv",
      "gerado_em": "...",
      "pesquisas": [
        {"aba", "linha",
         "dataset": {"type", "name", "title", "tema", ...},   # pronto para o `package_create`
         "recursos": [{"tipo_documento", "caminho_arquivo", "name", "format", "mimetype"}],
         "avisos": [...]}                                      # o que não coube no schema
      ]
    }

Limpeza (veja `scripts/README.md` para os problemas da planilha):

- todas as colunas: tira caracteres invisíveis e espaços repetidos, corrige erros de digitação
  (`CORRECOES`) e troca os marcadores de vazio (`0`, `#N/A`, `#VALUE!`, `-`, `N/a`) por nada;
- título: tira a caixa alta, mantendo siglas e nomes próprios;
- colunas com opções no schema (tema, etapa, tipo de estudo, observatório, recorte): convertidas
  para os valores do schema, por apelido ou pelo texto;
- colunas de lista (público, tópico, apoio, realização): divididas, com grafias unificadas;
- palavras-chave: tags válidas do CKAN, em minúsculas (menos siglas e nomes próprios);
- resumo: partes separadas por `//` viram parágrafos e comentários `[Nome: ...]` saem;
- tradução: separada em título alternativo e termos de busca.
"""

import json
import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import PurePosixPath

import pandas as pd

from .constants import (
    APELIDOS_ETAPA,
    APELIDOS_TEMA,
    ASPAS,
    CAMPOS_OBRIGATORIOS,
    CARACTERES_INVISIVEIS,
    COL_ALAVANCA,
    COL_ANO,
    COL_APOIO,
    COL_ETAPA,
    COL_FICHA_SITE,
    COL_FORMATO,
    COL_OBJETIVO,
    COL_OBS,
    COL_OBSERVATORIO,
    COL_PALAVRAS_CHAVE,
    COL_PUBLICO,
    COL_REALIZACAO,
    COL_RECORTE,
    COL_RELATORIO,
    COL_RESUMO,
    COL_RESUMO_2,
    COL_SUMARIO,
    COL_TEMA,
    COL_TIPO_ESTUDO,
    COL_TITULO,
    COL_TOPICO,
    COL_TRADUCAO,
    COLUNAS_LINK,
    CORRECOES,
    CSV_CAMPO_CAMINHO_ARQUIVO,
    CSV_CAMPO_STATUS,
    CSV_COLUNA_ABA,
    CSV_COLUNA_LINHA,
    CSV_ENCODING,
    CSV_NOME,
    CSV_PREFIXO_RECURSO,
    DATASET_TYPE,
    DEFAULT_SAIDA_DIR,
    DOWNLOAD_SEM_LINK,
    EXTENSOES_ACEITAS,
    FORMATOS_ARQUIVO,
    JSON_NOME,
    MARCA_DUVIDA,
    MARCAS_NAO_PUBLICAR,
    OPCOES_ETAPA,
    OPCOES_OBSERVATORIO,
    OPCOES_RECORTE,
    OPCOES_TEMA,
    OPCOES_TIPO_ESTUDO,
    PARAGRAFO,
    PONTUACAO_FINAL,
    PROPORCAO_MAIUSCULAS,
    RE_COMENTARIO_INTERNO,
    RE_ESPACO_ANTES_PONTUACAO,
    RE_ESPACOS,
    RE_LINHAS_EM_BRANCO,
    RE_SECAO_TRADUCAO,
    RE_TAG_CARACTERES_INVALIDOS,
    RE_TITULO_SUBLINHADO,
    SECAO_PALAVRAS_CHAVE,
    SECAO_TITULO,
    SEPARADOR_PARTES_RESUMO,
    SEPARADOR_SECOES_TRADUCAO,
    SEPARADOR_TAG_STRING,
    SEPARADORES_ETAPA,
    SEPARADORES_LISTAS,
    SEPARADORES_PALAVRAS_CHAVE,
    SEPARADORES_PALAVRAS_CHAVE_TRADUCAO,
    SEPARADORES_RECORTE,
    SEPARADORES_TERMOS_BUSCA,
    SIGLAS,
    SINONIMOS,
    SLUG_MAX_LEN,
    TAG_MAX_LEN,
    TAG_MIN_LEN,
    TAMANHO_MIN_PALAVRA_MAIUSCULA,
    TERMOS_PROPRIOS,
    TITULO_SUBLINHADO_POR,
    VALORES_FORA_DO_LUGAR,
    VALORES_NULOS,
)

# --------------------------------------------------------------------------------------------
# Funções auxiliares
# --------------------------------------------------------------------------------------------


def slugify(texto: str, separador: str = "-") -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", separador, texto.lower()).strip(separador)


def limpar(texto: str) -> str | None:
    """Texto sem caracteres invisíveis, espaços repetidos e erros de digitação; None se vazio."""
    for caractere in CARACTERES_INVISIVEIS:
        texto = texto.replace(caractere, "")
    # Mantém as quebras de linha: separam valores em `Recorte` e seções em `Tradução`.
    texto = "\n".join(re.sub(RE_ESPACOS, " ", linha).strip() for linha in texto.splitlines())
    texto = re.sub(RE_LINHAS_EM_BRANCO, PARAGRAFO, texto).strip()
    texto = re.sub(RE_ESPACO_ANTES_PONTUACAO, r"\1", texto)
    if not texto or texto in VALORES_NULOS:
        return None
    for errado, certo in CORRECOES.items():
        texto = re.sub(errado, certo, texto)
    return texto


def dividir(texto: str | None, separadores: tuple[str, ...]) -> list[str]:
    """Partes sem repetição, divididas nos separadores, exceto dentro de parênteses."""
    partes: list[str] = []
    atual = ""
    nivel = 0
    i = 0
    while texto and i < len(texto):
        separador = next((s for s in separadores if texto.startswith(s, i)), None)
        if separador and nivel == 0:
            partes.append(atual)
            atual = ""
            i += len(separador)
            continue
        nivel += {"(": 1, ")": -1}.get(texto[i], 0)
        nivel = max(nivel, 0)
        atual += texto[i]
        i += 1
    partes.append(atual)
    vistos: set[str] = set()
    resultado = []
    for parte in partes:
        parte = parte.strip().rstrip(".;,").strip()
        if parte and parte.casefold() not in vistos and parte not in VALORES_NULOS:
            vistos.add(parte.casefold())
            resultado.append(parte)
    return resultado


def para_opcoes(
    texto: str, opcoes: tuple[str, ...], apelidos: dict, separadores: tuple[str, ...] = ()
) -> tuple[list[str], list[str]]:
    """Valores do schema para o texto (por apelido ou pelo próprio texto) e trechos sem opção."""
    apelidos = {slugify(apelido, "_"): valores for apelido, valores in apelidos.items()}
    inteiro = slugify(texto, "_")
    partes = [texto] if inteiro in apelidos or inteiro in opcoes else dividir(texto, separadores)
    escolhidas: list[str] = []
    sem_opcao: list[str] = []
    for parte in partes:
        slug = slugify(parte, "_")
        if slug in apelidos:
            escolhidas.extend(apelidos[slug])
        elif slug in opcoes:
            escolhidas.append(slug)
        else:
            sem_opcao.append(parte)
    # Na ordem do schema.
    return [o for o in opcoes if o in escolhidas], sem_opcao


def com_termos_proprios(texto: str) -> str:
    for termo in TERMOS_PROPRIOS:
        texto = re.sub(rf"\b{re.escape(termo)}\b", termo, texto, flags=re.IGNORECASE)
    return texto


# --------------------------------------------------------------------------------------------
# Leitura e limpeza das colunas
# --------------------------------------------------------------------------------------------

csv_path = DEFAULT_SAIDA_DIR / CSV_NOME
json_path = DEFAULT_SAIDA_DIR / JSON_NOME

df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding=CSV_ENCODING)
df.columns = [coluna.strip() for coluna in df.columns]
colunas_planilha = [
    c
    for c in df.columns
    if c not in (CSV_COLUNA_ABA, CSV_COLUNA_LINHA) and not c.startswith(CSV_PREFIXO_RECURSO)
]
for coluna in colunas_planilha:
    df[coluna] = df[coluna].map(limpar)
# Vazios como None (e não NaN, que é verdadeiro em `if valor`).
df = df.astype(object).where(df.notna(), None)

# Colunas de lista: divididas, com sinônimos trocados e cada valor na grafia mais comum da
# coluna (`Formação de Professores` e `Formação de professores` viram a mesma).
listas: dict[str, list[list[str]]] = {}
for coluna, separadores in SEPARADORES_LISTAS.items():
    itens = [[SINONIMOS.get(i, i) for i in dividir(valor, separadores)] for valor in df[coluna]]
    grafias: dict[str, str] = {}
    for item, _ in Counter(i for lista in itens for i in lista).most_common():
        grafias.setdefault(item.casefold(), item)
    listas[coluna] = [list(dict.fromkeys(grafias[i.casefold()] for i in lista)) for lista in itens]

tipos_documento = list(dict.fromkeys(COLUNAS_LINK.values()))

# --------------------------------------------------------------------------------------------
# Uma pesquisa por linha
# --------------------------------------------------------------------------------------------

pesquisas = []
nomes_usados: set[str] = set()
for i, linha in enumerate(df.to_dict("records")):
    dataset: dict[str, object] = {"type": DATASET_TYPE}
    avisos: list[str] = []

    # Título: `_ ` de nome de arquivo vira `: `; caixa alta vira minúscula, menos siglas.
    titulo = re.sub(RE_TITULO_SUBLINHADO, TITULO_SUBLINHADO_POR, linha[COL_TITULO])
    letras = [c for c in titulo if c.isalpha()]
    em_maiusculas = sum(c.isupper() for c in letras) / len(letras) > PROPORCAO_MAIUSCULAS
    palavras = re.split(r"(\w+)", titulo)
    for j, palavra in enumerate(palavras):
        maiuscula = palavra.isupper() and palavra not in SIGLAS
        if maiuscula and (em_maiusculas or len(palavra) >= TAMANHO_MIN_PALAVRA_MAIUSCULA):
            palavras[j] = palavra.lower()
    titulo = com_termos_proprios("".join(palavras))
    dataset["title"] = titulo[:1].upper() + titulo[1:]

    # `name`: slug do título. Títulos repetidos recebem o ano e, se ainda repetir, um número.
    base = slugify(dataset["title"])[:SLUG_MAX_LEN].strip("-")
    nome = base
    if nome in nomes_usados and linha[COL_ANO]:
        nome = f"{base}-{linha[COL_ANO]}"
    n = 1
    while nome in nomes_usados:
        n += 1
        nome = f"{base}-{n}"
    nomes_usados.add(nome)
    dataset["name"] = nome

    # Tema, tipo de estudo e observatório: uma opção do schema.
    for coluna, campo, opcoes, apelidos in (
        (COL_TEMA, "tema", OPCOES_TEMA, APELIDOS_TEMA),
        (COL_TIPO_ESTUDO, "tipo_estudo", OPCOES_TIPO_ESTUDO, {}),
        (COL_OBSERVATORIO, "observatorio", OPCOES_OBSERVATORIO, {}),
    ):
        if not linha[coluna]:
            continue
        escolhidas, _ = para_opcoes(linha[coluna], opcoes, apelidos)
        if len(escolhidas) == 1:
            dataset[campo] = escolhidas[0]
        else:
            avisos.append(f"{coluna}: {linha[coluna]!r} sem opção em `{campo}`")
        if MARCA_DUVIDA in linha[coluna]:
            avisos.append(f"{coluna}: {linha[coluna]!r} tem marca de dúvida")

    # Etapa e recorte: várias opções do schema.
    for coluna, campo, opcoes, apelidos, separadores in (
        (COL_ETAPA, "etapa", OPCOES_ETAPA, APELIDOS_ETAPA, SEPARADORES_ETAPA),
        (COL_RECORTE, "recorte", OPCOES_RECORTE, {}, SEPARADORES_RECORTE),
    ):
        if not linha[coluna]:
            continue
        escolhidas, sem_opcao = para_opcoes(linha[coluna], opcoes, apelidos, separadores)
        if escolhidas:
            dataset[campo] = escolhidas
        avisos.extend(f"{coluna}: {parte!r} sem opção em `{campo}`" for parte in sem_opcao)

    if linha[COL_ALAVANCA]:
        dataset["alavanca"] = linha[COL_ALAVANCA]

    if linha[COL_ANO]:
        if linha[COL_ANO].isdigit():
            dataset["ano"] = int(linha[COL_ANO])
        else:
            avisos.append(f"{COL_ANO}: {linha[COL_ANO]!r} não é um ano")

    # Palavras-chave: `Não publicar` é instrução, não tag. A pesquisa vai como privada.
    palavras = linha[COL_PALAVRAS_CHAVE] or ""
    if any(marca in palavras.casefold() for marca in MARCAS_NAO_PUBLICAR):
        dataset["private"] = True
        avisos.append(f"{COL_PALAVRAS_CHAVE}: {palavras!r}; publicada como privada")
        palavras = ""
    tags = []
    for parte in dividir(palavras, SEPARADORES_PALAVRAS_CHAVE):
        tag = re.sub(RE_TAG_CARACTERES_INVALIDOS, " ", parte)
        tag = re.sub(r"\s+", " ", tag).strip(" .-")
        # Minúsculas, menos siglas e palavras com maiúscula no meio (`AvaMEC`).
        tag = "".join(p if p[1:] != p[1:].lower() else p.lower() for p in re.split(r"(\w+)", tag))
        tag = com_termos_proprios(tag)
        if TAG_MIN_LEN <= len(tag) <= TAG_MAX_LEN and tag not in tags:
            tags.append(tag)
    if tags:
        dataset["tag_string"] = SEPARADOR_TAG_STRING.join(tags)

    # Público, tópico, apoio e realização: listas, sem os valores digitados na coluna errada.
    for coluna, campo in (
        (COL_PUBLICO, "publico"),
        (COL_TOPICO, "topico"),
        (COL_APOIO, "apoio"),
        (COL_REALIZACAO, "realizacao"),
    ):
        valores = []
        for valor in listas[coluna][i]:
            if valor in VALORES_FORA_DO_LUGAR.get(coluna, ()):
                avisos.append(f"{coluna}: {valor!r} parece ser de outra coluna; descartado")
            else:
                valores.append(valor)
            if MARCA_DUVIDA in valor:
                avisos.append(f"{coluna}: {valor!r} tem marca de dúvida")
        if valores:
            dataset[campo] = valores

    # Objetivo: texto, com a primeira letra maiúscula.
    objetivo = linha[COL_OBJETIVO]
    if objetivo in VALORES_FORA_DO_LUGAR[COL_OBJETIVO]:
        avisos.append(f"{COL_OBJETIVO}: {objetivo!r} parece ser de outra coluna; descartado")
        objetivo = None
    if objetivo:
        dataset["objetivo"] = objetivo[:1].upper() + objetivo[1:]

    # Resumo (`notes`): o primeiro `Resumo` preenchido. `//` vira parágrafo e comentários
    # internos (`[Danilo: ...]`) saem.
    resumo = linha[COL_RESUMO] or linha[COL_RESUMO_2]
    if resumo:
        for comentario in re.findall(RE_COMENTARIO_INTERNO, resumo):
            avisos.append(f"{COL_RESUMO}: comentário interno removido: {comentario.strip()!r}")
        resumo = re.sub(RE_COMENTARIO_INTERNO, "", resumo)
        partes = [p.strip() for p in resumo.split(SEPARADOR_PARTES_RESUMO) if p.strip()]
        resumo = PARAGRAFO.join(p[:1].upper() + p[1:] for p in partes).rstrip(";, ")
        if resumo and resumo[-1] not in PONTUACAO_FINAL:
            resumo += "."
        if resumo:
            dataset["notes"] = resumo

    # Tradução: seções `Título:`, `Palavras-chave:` e `Termos e frases...:`. Texto sem seção é o
    # título alternativo, a não ser que repita o título ou o objetivo.
    traducao = linha[COL_TRADUCAO]
    if traducao:
        traducao = traducao.replace(SEPARADOR_SECOES_TRADUCAO, "\n")
        antes, *secoes = re.split(RE_SECAO_TRADUCAO, traducao)
        titulo_alternativo = antes.strip().strip(ASPAS).strip() or None
        termos: list[str] = []
        for cabecalho, corpo in zip(secoes[::2], secoes[1::2], strict=True):
            secao = slugify(cabecalho, "_")
            if secao == SECAO_TITULO:
                titulo_alternativo = corpo.strip().strip(ASPAS).strip() or titulo_alternativo
            elif secao == SECAO_PALAVRAS_CHAVE:
                termos += dividir(corpo, SEPARADORES_PALAVRAS_CHAVE_TRADUCAO)
            else:
                termos += dividir(corpo, SEPARADORES_TERMOS_BUSCA)
        repetidos = {slugify(dataset["title"]), slugify(dataset.get("objetivo", ""))}
        if titulo_alternativo and slugify(titulo_alternativo) not in repetidos:
            dataset["titulo_alternativo"] = titulo_alternativo
        termos_busca: list[str] = []
        for termo in termos:
            termo = termo.strip(ASPAS).strip()
            if termo and termo.casefold() not in {t.casefold() for t in termos_busca}:
                termos_busca.append(termo)
        if termos_busca:
            dataset["termos_busca"] = termos_busca

    # Colunas sem campo no schema.
    if linha[COL_OBS]:
        avisos.append(f"{COL_OBS}: {linha[COL_OBS]!r} sem campo no schema CKAN")

    # Recursos: os arquivos baixados pelo `extrair_pesquisas.py`. O formato vem da extensão do
    # arquivo ou, sem extensão, da coluna `Formato do arquivo`.
    # `Não divulgar` nessa coluna já aparece no status do recurso (`nao_divulgar`).
    formato_planilha = FORMATOS_ARQUIVO.get(slugify(linha[COL_FORMATO] or "", "_"))
    recursos = []
    for tipo in tipos_documento:
        caminho = linha[f"{CSV_PREFIXO_RECURSO}{tipo}.{CSV_CAMPO_CAMINHO_ARQUIVO}"]
        status = linha[f"{CSV_PREFIXO_RECURSO}{tipo}.{CSV_CAMPO_STATUS}"]
        if not caminho:
            if status and status != DOWNLOAD_SEM_LINK:
                avisos.append(f"recurso `{tipo}`: arquivo não baixado ({status})")
            continue
        arquivo = PurePosixPath(caminho)
        extensao = arquivo.suffix.lstrip(".").lower()
        recurso = {
            "tipo_documento": tipo,
            "caminho_arquivo": caminho,
            "name": arquivo.name,
            "format": extensao.upper() or formato_planilha,
            "mimetype": EXTENSOES_ACEITAS.get(extensao),
        }
        recursos.append({k: v for k, v in recurso.items() if v is not None})
    # `Relatório`, `Sumário` e `Ficha site` às vezes têm um nome de arquivo, e não um link.
    for coluna in (COL_RELATORIO, COL_SUMARIO, COL_FICHA_SITE):
        tipo = COLUNAS_LINK[coluna]
        if linha[coluna] and not linha[f"{CSV_PREFIXO_RECURSO}{tipo}.{CSV_CAMPO_CAMINHO_ARQUIVO}"]:
            avisos.append(f"{coluna}: {linha[coluna]!r} não é um link; recurso não publicado")

    avisos.extend(
        f"`{campo}` vazio: campo obrigatório no CKAN"
        for campo in CAMPOS_OBRIGATORIOS
        if campo not in dataset
    )
    pesquisas.append(
        {
            "aba": linha[CSV_COLUNA_ABA],
            "linha": int(linha[CSV_COLUNA_LINHA]),
            "dataset": dataset,
            "recursos": recursos,
            "avisos": avisos,
        }
    )

# --------------------------------------------------------------------------------------------
# Saída
# --------------------------------------------------------------------------------------------

saida = {
    "fonte": csv_path.name,
    "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
    "pesquisas": pesquisas,
}
json_path.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
com_aviso = sum(bool(p["avisos"]) for p in pesquisas)
print(f"{len(pesquisas)} pesquisas ({com_aviso} com avisos) -> {json_path}")
