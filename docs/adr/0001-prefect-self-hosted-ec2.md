# ADR 0001: Prefect self-hosted na EC2 com work pool Docker

- Status: aceita
- Data: 2026-10-19

## Contexto

`docs/ORCHESTRATION.md` define o Prefect como orquestrador das pipelines, mas
não define onde a API executa nem como os flow runs executam. O projeto tem uma
EC2 dedicada ao orquestrador, provisionada pelo `mpb-infra`.

## Decisão

- A EC2 executa o Prefect 3 self-hosted (API e UI) com Docker Compose.
- O banco do Prefect é um Postgres na mesma EC2, com volume no disco EBS.
- Um worker do tipo Docker atende o work pool `mpb-docker`.
- Cada flow run executa em um container da imagem do repositório, publicada no ECR.
- Os deployments ficam em `prefect.yaml`. A tag da imagem é o hash do commit.
- A API não tem exposição pública. O acesso é pelo port forwarding do SSM, com basic auth.

## Alternativas consideradas

- Prefect Cloud: remove a operação do servidor, mas adiciona custo e uma
  dependência externa para os dados de execução.
- Work pool `process` com `git clone`: é mais simples, mas não isola as
  dependências entre flows e depende do ambiente Python da EC2.

## Consequências

- O time opera o servidor, o banco e os backups do Postgres.
- O `mpb-infra` entrega a EC2, o ECR, a IAM Role, o IMDSv2 com hop limit 2 e os segredos.
- O deploy ocorre na EC2 com `prefect deploy`. Um job de CD é uma decisão futura.
- Postgres em RDS pode substituir o container sem mudança de código
  (`PREFECT_API_DATABASE_CONNECTION_URL`).
