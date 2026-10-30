# Orquestração

Prefect 3 é o padrão adotado pela Base dos Dados para a orquestração das
pipelines deste projeto.

A EC2 do orquestrador executa o Prefect 3 self-hosted e um worker Docker. Os
flow runs executam em containers da imagem do repositório, publicada no ECR.
A decisão está em `docs/adr/0001-prefect-self-hosted-ec2.md`.

## Estrutura

- `src/mpb_data_pipelines/flows`: flows e tasks. O flow `healthcheck` é usado
  pelas verificações do CI/CD.
- `src/mpb_data_pipelines/s3.py`: task compartilhada `upload_file`, que envia
  arquivos às camadas do S3.
- `src/mpb_data_pipelines/ops/checks.py`: verificações antes e depois do deploy.
- `prefect.yaml`: definição dos deployments. O CI gera a imagem (`docs/adr/0002-ci-cd.md`).
- `Dockerfile`: imagem de execução dos flow runs.
- `orchestrator/`: Docker Compose da EC2 e passo a passo de operação.

## Organização dos flows

- Cada fonte de dados é um pacote em `src/mpb_data_pipelines/flows/<dataset>/`,
  com o flow na função `main` de `flow.py`. Tasks específicas da fonte (ex.:
  `download_raw_file` em `flows/dataset_exemplo/flow.py`) ficam no mesmo módulo.
- O envio às camadas do S3 é feito pela task compartilhada `upload_file`.
- Tasks com efeitos colaterais (downloads, uploads) usam `cache_policy=NO_CACHE`
  e `retries` explícitos.

## Novo flow

1. Crie o pacote em `src/mpb_data_pipelines/flows/<dataset>/`, com o flow em `flow.py:main`.
2. Adicione um item em `deployments` no `prefect.yaml`, com `version: "{{ $MPB_VERSION }}"`
   e `work_pool: *docker_pool`.
3. Adicione um teste que execute o flow dentro de `prefect.testing.utilities.prefect_test_harness`.
   O teste não deve depender de serviços de orquestração nem de credenciais AWS.

Airflow, MWAA ou outro orquestrador não devem ser introduzidos sem nova
decisão arquitetural.
