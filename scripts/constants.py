"""Constantes dos scripts de extração, limpeza e publicação das pesquisas."""

from pathlib import Path

# --------------------------------------------------------------------------------------------
# Arquivos
# --------------------------------------------------------------------------------------------

DEFAULT_PLANILHA = Path("input/teste_organização_observatório (4).xlsx")
# Diretório de saída: recebe o CSV, o JSON e os arquivos baixados. O `caminho_arquivo` de cada
# recurso é relativo a este diretório.
DEFAULT_SAIDA_DIR = Path("output")
CSV_NOME = "pesquisas.csv"  # gerado por `extrair_pesquisas.py`, lido por `clean.py`
JSON_NOME = "pesquisas.json"  # gerado por `clean.py`, lido por `publicar_ckan.py`
ARQUIVOS_SUBDIR = "arquivos"
# `utf-8-sig` (com BOM) para o Excel abrir o CSV com acentos corretos.
CSV_ENCODING = "utf-8-sig"
CSV_SEPARADOR_LISTA = " | "
# Colunas do CSV além das colunas da planilha.
CSV_COLUNA_ABA = "aba"
CSV_COLUNA_LINHA = "linha"
# Colunas de recurso: `recurso.<tipo_documento>.<campo>`.
CSV_PREFIXO_RECURSO = "recurso."
CSV_CAMPO_STATUS = "status"
CSV_CAMPO_CAMINHO_ARQUIVO = "caminho_arquivo"
CSV_CAMPOS_RECURSO = ("links", CSV_CAMPO_STATUS, CSV_CAMPO_CAMINHO_ARQUIVO, "erro")

# --------------------------------------------------------------------------------------------
# Planilha
# --------------------------------------------------------------------------------------------

# Abas lidas, uma por período. A aba `Metadados` (consolidado) é ignorada. Todas precisam ter o
# mesmo cabeçalho.
ABAS = ("2023", "2024", "2025-2026")
LINHA_CABECALHO = 1

# Cabeçalhos das colunas, sem os espaços nas pontas (`Título da Pesquisa ` tem um no fim).
COL_TITULO = "Título da Pesquisa"
COL_LINK = "Link acesso"
COL_TEMA = "Grupo temático"
COL_ALAVANCA = "Alavanca"
COL_ETAPA = "Etapa de ensino"
COL_PALAVRAS_CHAVE = "Palavras chave"
COL_TIPO_ESTUDO = "Tipo de estudo"
COL_FORMATO = "Formato do arquivo"
COL_ANO = "Ano"
COL_OBSERVATORIO = "Observatório"
COL_PUBLICO = "Público"
COL_TOPICO = "Tópico"
COL_OBJETIVO = "Objetivo"
COL_APOIO = "Apoio"
COL_REALIZACAO = "Realização"
COL_RECORTE = "Recorte"
COL_RESUMO = "Resumo"
# A planilha repete o cabeçalho `Resumo` (colunas Q e U); o pandas lê a segunda como `Resumo.1`.
COL_RESUMO_2 = "Resumo.1"
COL_TRADUCAO = "Tradução"
COL_RELATORIO = "Relatório"
COL_SUMARIO = "Sumário"
COL_FICHA_SITE = "Ficha site"
COL_OBS = "OBS"

# `tipo_documento` dos recursos (campo de recurso no schema).
TIPO_DOC_DOCUMENTO = "documento"
TIPO_DOC_RELATORIO = "relatorio"
TIPO_DOC_SUMARIO = "sumario_executivo"
TIPO_DOC_FICHA_SITE = "ficha_site"

# Colunas com o link de um recurso: cabeçalho -> `tipo_documento`.
COLUNAS_LINK = {
    COL_LINK: TIPO_DOC_DOCUMENTO,
    COL_RELATORIO: TIPO_DOC_RELATORIO,
    COL_SUMARIO: TIPO_DOC_SUMARIO,
    COL_FICHA_SITE: TIPO_DOC_FICHA_SITE,
}
# Colunas cujo texto pode marcar o arquivo de um recurso como "não divulgar".
COLUNAS_FORMATO = {COL_FORMATO: TIPO_DOC_DOCUMENTO}

# Marcações de "não divulgar" na coluna `Formato do arquivo`, na célula ou no link: o arquivo
# não é baixado nem publicado.
MARCAS_NAO_DIVULGAR = ("não divulgar", "nao divulgar", "nao_divulgar")

# --------------------------------------------------------------------------------------------
# Limpeza (`clean.py`)
# --------------------------------------------------------------------------------------------

# Valores que a planilha usa para "sem valor": VLOOKUP com célula de origem vazia (0), erros de
# fórmula do Excel (`#N/A` = título não encontrado na `Planilha3`) e marcações manuais.
VALORES_NULOS = frozenset(
    {"0", "-", "N/a", "N/A", "#N/A", "#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!"}
)

# Espaço de largura zero e afins: aparecem em títulos copiados de outros documentos.
CARACTERES_INVISIVEIS = ("​", "‌", "‍", "⁠", "﻿")
RE_ESPACOS = r"[ \t ]+"
RE_ESPACO_ANTES_PONTUACAO = r"[ \t]+([.,;:])(?=\s|$)"
RE_LINHAS_EM_BRANCO = r"\n{3,}"

# Erros de digitação encontrados na planilha (regex -> correção), aplicados em todas as colunas.
CORRECOES = {
    r"\bEudcação\b": "Educação",
    r"\bencaminahmento\b": "encaminhamento",
    r"\bcoletânia\b": "coletânea",
    r"\bColetânia\b": "Coletânea",
    r"\bterrotório\b": "território",
    r"\bdatransição\b": "da transição",
    r"\bahabilidades\b": "habilidades",
    r"\bldieranças\b": "lideranças",
    r"\binduçao\b": "indução",
    r"\bViidigal\b": "Vidigal",
    r"\bcarga horário\b": "carga horária",
    r"\banos anos\b": "anos",
    r"\bbem sucedidas\b": "bem-sucedidas",
    r"\bMunicipios vulneraveis\b": "Municípios vulneráveis",
    r"\bSintese\b": "Síntese",
    r"\bAvamec\b": "AvaMEC",
}

# Títulos: `Continuada_ Uma síntese` vem de nome de arquivo, em que `:` vira `_`.
RE_TITULO_SUBLINHADO = r"_\s+"
TITULO_SUBLINHADO_POR = ": "
# Palavras em maiúsculas viram minúsculas quando o título está quase todo em maiúsculas (mais
# que esta proporção de letras) ou quando têm pelo menos este tamanho. Siglas são mantidas.
PROPORCAO_MAIUSCULAS = 0.6
TAMANHO_MIN_PALAVRA_MAIUSCULA = 7
SIGLAS = frozenset(
    {
        "BNC", "BNCC", "CNE", "DCN", "DF", "EF", "EI", "EJA", "EM", "ENEM", "EPT", "ERER",
        "FUNDEB", "MEC", "MPB", "SAEB", "UF",
    }
)  # fmt: skip
# Nomes próprios com grafia fixa em títulos e palavras-chave (os mais longos primeiro).
TERMOS_PROPRIOS = (
    "Base Nacional Comum Curricular",
    "Novo Ensino Médio",
    "BNC-Computação",
    "Novo Fundeb",
    "AvaMEC",
    "Fundeb",
    "Ideb",
    "Saeb",
)

# Resumo: `//` separa partes do texto (viram parágrafos) e `[Nome: ...]` é comentário interno.
SEPARADOR_PARTES_RESUMO = "//"
PARAGRAFO = "\n\n"
RE_COMENTARIO_INTERNO = r"\s*\[[A-ZÀ-Ú][\wÀ-ú]*:[^\]]*\]"
PONTUACAO_FINAL = ".!?"

# Separadores das colunas com vários valores. `dividir` não divide dentro de parênteses.
SEPARADORES_ETAPA = (",", ";", " e ", "//", "\n")
SEPARADORES_PALAVRAS_CHAVE = (",", ";", "//", "\n")
SEPARADORES_RECORTE = (",", ";", "//", "\n")
SEPARADORES_LISTAS = {
    COL_PUBLICO: (";",),
    COL_TOPICO: (";", ","),
    COL_APOIO: (";", ","),
    COL_REALIZACAO: (";", ",", " e "),
}
# Grafias diferentes do mesmo valor nas colunas de lista. Diferenças só de maiúsculas e
# minúsculas são resolvidas pela grafia mais comum na coluna.
SINONIMOS = {
    "Análise de Políticas Públicas": "Analistas de Políticas Públicas",
    "Analítica": "Analistas de Políticas Públicas",
    "MPB": "Movimento pela Base",
    "MpB": "Movimento pela Base",
    "Danilo Dalmon": "Danilo Leite Dalmon",
}
# Valores digitados na coluna errada: são descartados com aviso.
VALORES_FORA_DO_LUGAR = {
    COL_PUBLICO: ("Tradução", "Estudo de caso"),
    COL_OBJETIVO: ("Análise",),
}
# Marca de dúvida deixada por quem preencheu (`Não?`, `MPB?`): o valor é usado, com aviso.
MARCA_DUVIDA = "?"

# Instrução na coluna `Palavras chave`: a pesquisa é publicada como privada.
MARCAS_NAO_PUBLICAR = ("não publicar", "nao publicar")

# `Formato do arquivo` (slug) -> formato do recurso, usado quando o arquivo não tem extensão.
FORMATOS_ARQUIVO = {"pdf": "PDF", "word": "DOCX", "ppt": "PPTX", "excel": "XLSX"}

# Tradução: seções `Título:`, `Palavras-chave:` e `Termos e frases para otimização de busca:`,
# separadas por quebra de linha ou por `//`. Texto sem seção é um título alternativo.
SEPARADOR_SECOES_TRADUCAO = "//"
RE_SECAO_TRADUCAO = (
    r"(?im)^[ \t]*(t[íi]tulo|palavras[- ]chave|termos e frases para otimiza[çc][ãa]o de busca)"
    r"[ \t]*:"
)
SECAO_TITULO = "titulo"
SECAO_PALAVRAS_CHAVE = "palavras_chave"
SEPARADORES_PALAVRAS_CHAVE_TRADUCAO = (",", ";", "\n")
SEPARADORES_TERMOS_BUSCA = (";", "\n")
ASPAS = "\"'“”"

# Tamanho máximo do slug antes do sufixo de desempate (o CKAN aceita até 100 caracteres).
SLUG_MAX_LEN = 90

# --------------------------------------------------------------------------------------------
# Schema `pesquisa` do CKAN
# --------------------------------------------------------------------------------------------
# Schema: mpb_ckan/src/ckanext-mpb/ckanext/mpb/schemas/pesquisa.yaml. Todas as colunas são
# enviadas; o CKAN decide o que é público ou privado (`mpb_private`).

DATASET_TYPE = "pesquisa"

OPCOES_TEMA = ("conteudo_curricular", "implementacao", "revisao_politica_curricular")
# `Políticas Educacionais` e `Ensino e aprendizagem` não têm opção no schema: ficam de fora
# com aviso.
APELIDOS_TEMA = {
    "Conteúdos e competências": ("conteudo_curricular",),
    "Implementação da BNCC": ("implementacao",),
    "Revisão de política curricular": ("revisao_politica_curricular",),
}

OPCOES_ETAPA = ("educacao_infantil", "ensino_fundamental", "ensino_medio")
APELIDOS_ETAPA = {
    "Todas": OPCOES_ETAPA,
    "AF EF": ("ensino_fundamental",),
}

OPCOES_TIPO_ESTUDO = (
    "analise",
    "artigo",
    "benchmarking",
    "boa_pratica",
    "curso",
    "estudo_de_caso",
    "guia",
    "pesquisa",
    "recomendacoes",
    "traducao",
)

OPCOES_OBSERVATORIO = ("sim", "nao", "site_mpb")

OPCOES_RECORTE = ("brasil", "estadual", "municipal")

# Campos que o schema exige em todo conjunto de dados (`owner_org` vem do `publicar_ckan.py`).
CAMPOS_OBRIGATORIOS = ("title", "tag_string")

# O CKAN só aceita letras, números, espaço, `-`, `_` e `.` nas tags, com 2 a 100 caracteres.
RE_TAG_CARACTERES_INVALIDOS = r"[^\w \-.]"
TAG_MIN_LEN = 2
TAG_MAX_LEN = 100
SEPARADOR_TAG_STRING = ","

# --------------------------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------------------------

# Status do download (campo `status` de cada recurso).
DOWNLOAD_OK = "baixado"
DOWNLOAD_SEM_LINK = "sem_link"
DOWNLOAD_NAO_DIVULGAR = "nao_divulgar"
DOWNLOAD_REQUER_AUTENTICACAO = "requer_autenticacao"
DOWNLOAD_NAO_E_ARQUIVO = "nao_e_arquivo"
DOWNLOAD_ERRO = "erro"
DOWNLOAD_PULADO = "pulado"

USER_AGENT = "mpb-data-pipelines/0.1"
DOWNLOAD_TIMEOUT_SECONDS = 60.0
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
DOWNLOAD_MAX_BYTES = 300 * 1024 * 1024

# Hosts que exigem login (o download anônimo devolve a página de login). Os arquivos são
# baixados com uma sessão do Playwright logada no SharePoint (veja abaixo).
HOSTS_AUTENTICADOS = ("sharepoint.com",)

# --------------------------------------------------------------------------------------------
# SharePoint (login com Playwright)
# --------------------------------------------------------------------------------------------

ENV_SHAREPOINT_USUARIO = "SHAREPOINT_USER"
ENV_SHAREPOINT_SENHA = "SHAREPOINT_PASSWORD"
# Página aberta para disparar o login da Microsoft.
SHAREPOINT_SITE_URL = "https://movimentopelabase.sharepoint.com/sites/PortalMovimentopelaBase"
# Cookies da sessão logada, reaproveitados entre execuções para não repetir o login (e o MFA).
# Contém credenciais de sessão: não versionar.
SHAREPOINT_ESTADO = Path(".sharepoint_state.json")
SHAREPOINT_ESTADO_PERMISSAO = 0o600
# Download direto de um arquivo, por caminho (`SourceUrl`) ou por id (`UniqueId`).
SHAREPOINT_DOWNLOAD_PATH = "/_layouts/15/download.aspx"
SHAREPOINT_LAYOUTS = "/_layouts/"
# `/:w:/r/sites/...`: prefixo de redirecionamento dos links do Office, antes do caminho do site.
RE_SHAREPOINT_PREFIXO_REDIRECIONAMENTO = r"^/:\w+:/r(?=/)"
SHAREPOINT_PARAM_CAMINHO = "id"  # `AllItems.aspx?id=<caminho do arquivo>`
SHAREPOINT_PARAM_DOCUMENTO = "sourcedoc"  # `Doc.aspx?sourcedoc={<id>}`
SHAREPOINT_PARAM_DOWNLOAD = "download=1"  # links de compartilhamento (`/:w:/s/...`)
# Tela de login da Microsoft.
SELETOR_EMAIL = "input[type=email]"
SELETOR_SENHA = "input[type=password]"
SELETOR_ENVIAR = "input[type=submit], button[type=submit]"
# "Continuar conectado?" depois da senha.
SELETOR_MANTER_CONECTADO = "#KmsiCheckboxField, [data-testid=kmsiVideo]"
# Tempo para concluir o login, incluindo o MFA feito à mão com `--sharepoint-visivel`.
SHAREPOINT_LOGIN_TIMEOUT_SECONDS = 300
SHAREPOINT_LOGIN_INTERVALO_MS = 1000
SHAREPOINT_PASSO_TIMEOUT_MS = 30_000
SHAREPOINT_ESPERA_PAGINA = "domcontentloaded"

GOOGLE_DRIVE_HOST = "drive.google.com"
GOOGLE_DOCS_HOST = "docs.google.com"
GOOGLE_DRIVE_DOWNLOAD_URL = "https://drive.usercontent.google.com/download"
GOOGLE_DOCS_EXPORT_FORMATS = {"document": "docx", "spreadsheets": "xlsx", "presentation": "pptx"}

# Extensões aceitas como arquivo de pesquisa e o mimetype de cada uma.
EXTENSOES_ACEITAS = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt": "application/vnd.oasis.opendocument.text",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "csv": "text/csv",
}
NOME_ARQUIVO_PADRAO = "arquivo"

# --------------------------------------------------------------------------------------------
# CKAN
# --------------------------------------------------------------------------------------------

# Arquivo com as variáveis abaixo (não versionado). Variáveis já definidas no ambiente têm
# precedência sobre o arquivo.
ENV_ARQUIVO = Path(".env")
ENV_CKAN_URL = "CKAN_URL"
ENV_CKAN_API_KEY = "CKAN_API_KEY"
ENV_CKAN_OWNER_ORG = "CKAN_OWNER_ORG"
CKAN_API_PATH = "/api/3/action/"
CKAN_TIMEOUT_SECONDS = 120.0
CKAN_NOT_FOUND_ERROR = "Not Found Error"
