# Contribuição

O repositório tem duas branches permanentes e protegidas:

- `dev`: integração. Recebe os Pull Requests das branches curtas.
- `main`: produção. Recebe Pull Requests somente de `dev`.

```
feature/* fix/* chore/* docs/*  --PR-->  dev  --PR-->  main
```

## Branches

Crie a branch a partir de `dev` com `feature/<descricao>`, `fix/<descricao>`,
`chore/<descricao>` ou `docs/<descricao>`. Abra o Pull Request para `dev`.
Mantenha a branch pequena, atualize-a com `dev` quando necessário e remova-a
após o merge. A promoção para produção é um Pull Request de `dev` para `main`.
O check `Source branch policy` bloqueia PRs para `main` vindos de outra branch.

## CI/CD

- `.github/workflows/pull-request.yml`: em todo PR para `dev` ou `main`, executa
  lint, testes e build do pacote (`.github/workflows/_checks.yml`).
- `.github/workflows/post-merge.yml`: após o merge em `dev` ou `main`, executa
  os checks no commit de merge, gera o build e faz o deploy desse artefato no
  ambiente correspondente (`dev` ou `production`).

Nesta etapa o deploy é um placeholder: ele recebe o artefato e não publica em
nenhum destino.

## Validação local

Use [uv](https://docs.astral.sh/uv/). O arquivo `.python-version` fixa o Python
3.11, a mesma versão do CI e das imagens Docker, e o uv baixa essa versão
automaticamente. Não use uma versão mais nova: o Python 3.15 não tem wheel do
`ruamel-yaml-clib`, e no Windows o `uv sync` falha pedindo o Microsoft C++ Build Tools.

Os comandos abaixo repetem os checks do CI (`.github/workflows/_checks.yml`):

```bash
uv sync --locked
uv run pre-commit install
uv run ruff check .
uv run ruff format --check .
uv run python -c 'import mpb_data_pipelines'
uv run python -m compileall -q src
uv run pytest -q
```

O teste de integração do orquestrador exige Docker e Bash (no Windows, use o
Git Bash ou o WSL):

```bash
docker build -t mpb-flows:local .
orchestrator/bin/integration-test.sh mpb-flows:local
```

Ele sobe uma stack Prefect descartável, registra os deployments, executa o flow
`healthcheck` e remove a stack (veja `orchestrator/README.md`).

As constantes de cada pacote ficam no `constants.py` do próprio diretório
(veja `CLAUDE.md`).

`pre-commit install` instala dois hooks Git. No `git commit`, o Ruff corrige e
formata os arquivos em stage; se houver mudança, o commit é bloqueado para
revisão e novo `git add`. No `git push`, o Ruff verifica o repositório inteiro,
como o CI. `--no-verify` ignora os hooks, mas não evita o check `Python lint`
no Pull Request.

Novas dependências entram com `uv add` (ou `uv add --dev`); o `uv.lock` é
versionado e o CI falha se ele estiver desatualizado.

O CI não usa fontes reais nem credenciais AWS estáticas. PRs do próprio
repositório assumem por OIDC uma role que apenas envia a imagem dos flows ao
ECR. O teste de integração sobe uma stack Prefect local e descartável. O deploy
ocorre no merge para `main`, pelo workflow `CD` (veja `docs/adr/0002-ci-cd.md`).
Segredos, `.env` e dados sensíveis nunca são versionados. Mudanças de schema e
contratos devem ser explícitas no PR; mudanças em decisões arquiteturais
existentes exigem ADR.

Pull Requests abertos pelo Dependabot seguem os mesmos checks e revisão; não
há merge automático de atualizações.
