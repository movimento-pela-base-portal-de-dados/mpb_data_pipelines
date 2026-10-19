# Orquestração

Prefect é o padrão adotado pela Base dos Dados para a orquestração das
pipelines deste projeto.

A EC2 do orquestrador executa o Prefect 3 self-hosted e um worker Docker. Os
flow runs executam em containers da imagem do repositório, publicada no ECR.
A decisão está em `docs/adr/0001-prefect-self-hosted-ec2.md`.

## Estrutura

- `src/mpb_data_pipelines/flows`: flows e tasks. Contém apenas orquestração.
  O único flow é `healthcheck`, usado pelas verificações do CI/CD.
- `src/mpb_data_pipelines/ops/checks.py`: verificações antes e depois do deploy.
- `connectors`, `transforms`, `quality`, `publish`: lógica de domínio em
  funções Python comuns, chamadas pelas tasks.
- `prefect.yaml`: definição dos deployments. O CI gera a imagem (`docs/adr/0002-ci-cd.md`).
- `Dockerfile`: imagem de execução dos flow runs.
- `orchestrator/`: Docker Compose da EC2 e passo a passo de operação.

## Novo flow

1. Crie o módulo em `src/mpb_data_pipelines/flows/`.
2. Adicione um item em `deployments` no `prefect.yaml`, com `version: "{{ $MPB_VERSION }}"`
   e `work_pool: *docker_pool`.
3. Adicione um teste que execute o flow dentro de `prefect.testing.utilities.prefect_test_harness`.

Airflow, MWAA ou outro orquestrador não devem ser introduzidos sem nova
decisão arquitetural.
