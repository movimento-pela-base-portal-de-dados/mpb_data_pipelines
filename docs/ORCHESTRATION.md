# Orquestração

Prefect 3 é o padrão adotado pela Base dos Dados para a orquestração das
pipelines deste projeto. Airflow, MWAA ou outro orquestrador não devem ser
introduzidos sem nova decisão arquitetural.

## Organização dos flows
- Cada fonte de dados é um pacote em `src/mpb_data_pipelines/flows/<dataset>/`,
  com o flow na função `main` de `flow.py`. Tasks específicas da fonte (ex.:
  `download_raw_file` em `flows/dataset_exemplo/flow.py`) ficam no mesmo módulo.
- O envio às camadas do S3 é feito pela task compartilhada `upload_file`, em
  `src/mpb_data_pipelines/s3.py`.
- Tasks com efeitos colaterais (downloads, uploads) usam `cache_policy=NO_CACHE`
  e `retries` explícitos.

## Pendências
Servidor ou Prefect Cloud, work pools, deployments e agendamentos ainda não estão
definidos. O CI executa os flows apenas com o backend temporário do
`prefect_test_harness`, sem serviços de orquestração nem credenciais AWS.
