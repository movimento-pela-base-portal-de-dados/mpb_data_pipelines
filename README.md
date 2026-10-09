# mpb-data-pipelines

Pipelines de aquisição, tratamento, validação e publicação de dados do Portal de Dados Movimento pela Base.

## Escopo
Fluxo esperado: fonte -> extração -> `S3/raw` -> validação/transformação -> `S3/processed` -> `S3/published` -> API CKAN.

A aplicação CKAN possui ciclo de vida independente. Este repositório não deve conter infraestrutura AWS nem código da aplicação CKAN.

## Estrutura
- `src/mpb_data_pipelines/connectors`: aquisição por API, arquivos, web e outras fontes.
- `transforms`: limpeza, padronização e enriquecimento.
- `quality`: regras e validações de qualidade.
- `publish`: publicação em S3 e integração com a API CKAN.
- `tests`: testes automatizados.
- `docs`: contratos e decisões técnicas.

## Repositórios relacionados
- `mpb-infra`: infraestrutura AWS/Terraform.
- `mpb-ckan`: aplicação e API CKAN.

## Preparação de engenharia

O desenvolvimento segue branches curtas e Pull Requests para `main`. Consulte
`CONTRIBUTING.md` e `.github/BRANCH_PROTECTION.md` para os quality gates.

Prefect é o padrão futuro de orquestração adotado pela Base dos Dados, conforme
`docs/ORCHESTRATION.md`. Ele não é instalado nem configurado nesta etapa.
