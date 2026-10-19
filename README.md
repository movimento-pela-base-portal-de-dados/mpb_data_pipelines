# mpb-data-pipelines

Pipelines de aquisição, tratamento, validação e publicação de dados do Portal de Dados Movimento pela Base.

## Escopo
Fluxo esperado: fonte -> extração -> `S3/raw` -> validação/transformação -> `S3/processed` -> `S3/published` -> API CKAN.

A aplicação CKAN possui ciclo de vida independente. Este repositório não deve conter infraestrutura AWS nem código da aplicação CKAN.

## Estrutura
- `src/mpb_data_pipelines/flows`: flows e tasks Prefect (apenas orquestração).
- `src/mpb_data_pipelines/connectors`: aquisição por API, arquivos, web e outras fontes.
- `transforms`: limpeza, padronização e enriquecimento.
- `quality`: regras e validações de qualidade.
- `publish`: publicação em S3 e integração com a API CKAN.
- `tests`: testes automatizados.
- `docs`: contratos e decisões técnicas.

## Repositórios relacionados
- `mpb-infra`: infraestrutura AWS/Terraform.
- `mpb-ckan`: aplicação e API CKAN.

## Início rápido

Requer Python 3.11+ e [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # cria .venv com dependências de desenvolvimento
uv run pre-commit install    # instala os hooks de commit e push
```

Os hooks executam o Ruff (lint e formatação):
- `git commit`: corrige os arquivos em stage. Se algo mudar, o commit é bloqueado; revise, faça `git add` e repita.
- `git push`: verifica o repositório inteiro, como o check `Python lint` do CI.

Para executar manualmente: `uv run pre-commit run --all-files`.

## Preparação de engenharia

O desenvolvimento segue branches curtas com Pull Requests para `dev`. A
promoção para produção é um Pull Request de `dev` para `main`. Consulte
`CONTRIBUTING.md` e `.github/BRANCH_PROTECTION.md` para os quality gates e o
fluxo de CI/CD.

## Orquestração

As pipelines executam no Prefect 3 self-hosted, na EC2 do orquestrador, com um
worker Docker. Consulte `docs/ORCHESTRATION.md` para a estrutura e
`orchestrator/README.md` para a operação e o CI/CD. Ainda não há flows de dados implementados.
