# Contribuição

O repositório usa desenvolvimento baseado em `main`: a branch é protegida e
toda mudança entra por Pull Request a partir de uma branch curta.

## Branches

Use `feature/<descricao>`, `fix/<descricao>`, `chore/<descricao>` ou
`docs/<descricao>`. Mantenha a branch pequena, atualize-a com `main` quando
necessário e remova-a após o merge. Não há branches permanentes `develop` ou
`release/*`.

## Validação local

Use Python 3.11 ou superior:

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
python -m pip check
python -c 'import mpb_data_pipelines'
pytest -q
```

O CI não usa credenciais AWS, fontes reais ou serviços de orquestração.
Segredos, `.env` e dados sensíveis nunca são versionados. Mudanças de schema e
contratos devem ser explícitas no PR; mudanças em decisões arquiteturais
existentes exigem ADR.

Pull Requests abertos pelo Dependabot seguem os mesmos checks e revisão; não
há merge automático de atualizações.
