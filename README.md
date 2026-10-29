# mpb-data-pipelines

Pipelines de aquisição, tratamento, validação e publicação de dados do Portal de Dados Movimento pela Base.

## Escopo
Fluxo esperado: fonte -> extração -> `S3/raw` -> validação/transformação -> `S3/processed` -> `S3/published` -> API CKAN.

A aplicação CKAN possui ciclo de vida independente. Este repositório não deve conter infraestrutura AWS nem código da aplicação CKAN.

## Estrutura
- `src/mpb_data_pipelines/flows/<dataset>/flow.py`: flow Prefect de cada fonte de dados, com
  extração, transformação e envio às camadas do S3.
- `src/mpb_data_pipelines/flows/healthcheck.py`: flow usado pelas verificações do CI/CD.
- `src/mpb_data_pipelines/s3.py`: envio de arquivos às camadas `raw`, `processed` e `published`.
- `src/mpb_data_pipelines/ops`: verificações antes e depois do deploy.
- `orchestrator`: Docker Compose da EC2 do orquestrador e passo a passo de operação.
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

O desenvolvimento segue branches curtas com Pull Requests para `staging`. A
promoção para produção é um Pull Request de `staging` para `main`. Consulte
`CONTRIBUTING.md` e `.github/BRANCH_PROTECTION.md` para os quality gates e o
fluxo de CI/CD.

## Orquestração com Prefect

Os pipelines são flows [Prefect 3](https://docs.prefect.io/v3/) e executam no
Prefect self-hosted, na EC2 do orquestrador, com um worker Docker. Consulte
`docs/ORCHESTRATION.md` para a estrutura e `orchestrator/README.md` para a
operação e o CI/CD. Cada fonte de dados tem seu pacote em
`src/mpb_data_pipelines/flows/<dataset>/`, com o flow na função `main` de `flow.py`;
`flows/dataset_exemplo/` é o modelo genérico (download -> `raw` -> transformação ->
`processed` -> `published`) a ser copiado para novas fontes.

Arquivos locais ficam em `<dataset>/<tabela>/`, relativo ao diretório de execução.
`s3.upload_file(s3.Layer.RAW, "<dataset>/<tabela>/<arquivo>")`, em `mpb_data_pipelines/s3.py`, envia o
arquivo para a chave `raw/<dataset>/<tabela>/<arquivo>`. O bucket é lido de
`MPB_S3_BUCKET` e as credenciais seguem a cadeia padrão do boto3.

Para executar um flow localmente (sem servidor, o Prefect sobe um backend temporário):

```bash
export MPB_S3_BUCKET=<bucket>
uv run python -c "
from mpb_data_pipelines.flows.dataset_exemplo.flow import main
main(url='https://exemplo.org/dados.csv')
"
```

Os testes usam `moto` para simular o S3 e não acessam a AWS.
