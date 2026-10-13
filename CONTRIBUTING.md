# Contribuição

O repositório usa desenvolvimento baseado em `main`: a branch é protegida e
toda mudança entra por Pull Request a partir de uma branch curta.

## Branches

Use `feature/<descricao>`, `fix/<descricao>`, `chore/<descricao>` ou
`docs/<descricao>`. Mantenha a branch pequena, atualize-a com `main` quando
necessário e remova-a após o merge. Não há branches permanentes `develop` ou
`release/*`.

## Validação local

Use Python 3.11 ou superior e [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
uv run python -c 'import mpb_data_pipelines'
uv run pytest -q
```

`pre-commit install` instala dois hooks Git. No `git commit`, o Ruff corrige e
formata os arquivos em stage; se houver mudança, o commit é bloqueado para
revisão e novo `git add`. No `git push`, o Ruff verifica o repositório inteiro,
como o CI. `--no-verify` ignora os hooks, mas não evita o check `Python lint`
no Pull Request.

Novas dependências entram com `uv add` (ou `uv add --dev`); o `uv.lock` é
versionado e o CI falha se ele estiver desatualizado.

O CI não usa credenciais AWS, fontes reais ou serviços de orquestração.
Segredos, `.env` e dados sensíveis nunca são versionados. Mudanças de schema e
contratos devem ser explícitas no PR; mudanças em decisões arquiteturais
existentes exigem ADR.

Pull Requests abertos pelo Dependabot seguem os mesmos checks e revisão; não
há merge automático de atualizações.
