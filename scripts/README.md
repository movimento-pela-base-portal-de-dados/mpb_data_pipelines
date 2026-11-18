# Scripts de pesquisas

1. `extrair_pesquisas.py`: lê as abas `2023`, `2024` e `2025-2026` (ignora a `Metadados`), grava
   `output/pesquisas.csv` com os valores brutos da planilha (sem tratamento) e baixa os arquivos.
   Os links do SharePoint são baixados com o Playwright, logado com a conta do `.env`.
2. `clean.py`: limpa e normaliza o CSV (erros de digitação, marcadores de vazio, caixa alta,
   separadores, opções do schema) e grava `output/pesquisas.json`, já no schema `pesquisa` do
   CKAN, com os avisos do que não coube.
3. `publicar_ckan.py`: lê o `output/pesquisas.json` e publica no CKAN, sem alterar os dados.
   `--dry-run` mostra o que seria enviado.

`constants.py` tem as constantes dos três, incluindo as regras de limpeza (`CORRECOES`,
`SINONIMOS`, `SIGLAS`, apelidos das opções).

```sh
uv run playwright install chromium   # uma vez, para o download do SharePoint
uv run python -m scripts.extrair_pesquisas [--sem-download] [--sharepoint-visivel]
uv run python -m scripts.clean
uv run python -m scripts.publicar_ckan [--dry-run]
```

Variáveis do `.env` na raiz do repositório (não versionado). Variáveis definidas no ambiente
têm precedência sobre o arquivo.

- `extrair_pesquisas.py`: `SHAREPOINT_USER` e `SHAREPOINT_PASSWORD`. O script faz o login da
  Microsoft e guarda a sessão em `.sharepoint_state.json` (não versionado), reaproveitada nas
  próximas execuções. Se a conta pedir MFA, use `--sharepoint-visivel` e conclua a verificação na
  janela do navegador.
- `publicar_ckan.py`: `CKAN_URL`, `CKAN_API_KEY` e `CKAN_OWNER_ORG`.
