# Orquestrador Prefect (EC2)

Esta pasta contém o runtime Prefect da EC2 do orquestrador:

- `postgres`: banco do Prefect, com volume no disco EBS.
- `prefect-server`: API e UI, em `127.0.0.1:4200`.
- `prefect-worker`: worker do work pool `mpb-docker`. Cada flow run executa em um
  container da imagem publicada no ECR (`Dockerfile` na raiz do repositório).
- `bin/`: scripts usados pelo CI, pelo CD e no teste local.

A EC2, o ECR, as roles e os segredos são provisionados pelo `mpb-infra`
(veja `docs/CONTRACTS.md`). As decisões estão em `docs/adr/0001-prefect-self-hosted-ec2.md`
e `docs/adr/0002-ci-cd.md`.

## Scripts

| Script | Uso |
|---|---|
| `bin/integration-test.sh IMAGEM` | Teste pré-deploy: sobe a stack com valores de teste, registra os deployments, verifica e remove a stack. |
| `bin/deploy.sh IMAGEM VERSAO` | Na EC2: gera o `.env` a partir do SSM, baixa a imagem, atualiza os serviços e registra os deployments. |
| `bin/register.sh IMAGEM VERSAO` | Registra os deployments do `prefect.yaml` com a própria imagem. |
| `bin/check.sh IMAGEM` | Verifica a API, o work pool, a imagem dos deployments e executa o flow `healthcheck`. |

## CI/CD

1. **PR**: `Python lint`, `Python tests and imports` e `Image / Image build and integration`.
   O último gera a imagem `tree-<hash>`, executa `bin/integration-test.sh` e envia a imagem ao ECR.
2. **Merge na `main`**: o workflow `CD` encontra a imagem do PR no ECR e executa
   `bin/deploy.sh` na EC2 por SSM Run Command.
3. **Pós-deploy**: o CD executa `bin/check.sh` na EC2. Se o deploy ou as
   verificações falham, o CD volta para a última versão aprovada.

Redeploy ou rollback manual: **Actions → CD → Run workflow**, com o commit em `ref`.

### Configuração no GitHub (administrador)

- Environment `production`, limitado à branch `main`.
- Variáveis do repositório: `AWS_REGION`, `ECR_REPOSITORY` (URI completa),
  `AWS_ROLE_CI_ARN`, `AWS_ROLE_CD_ARN` e `ORCHESTRATOR_INSTANCE_ID`.
- Nenhum secret. Sem `AWS_ROLE_CI_ARN`, o PR não envia a imagem. Sem
  `AWS_ROLE_CD_ARN`, o CD não executa.

## Primeira instalação da EC2

O mpb-infra entrega a EC2 com o clone em `/opt/mpb_data_pipelines` e os
parâmetros em `/mpb/prefect/`. O primeiro merge com as variáveis configuradas
faz o deploy completo. Antes disso, o CD não tem versão aprovada para rollback.

Acesse a UI pelo túnel SSM:

```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["4200"],"localPortNumber":["4200"]}'
```

Abra `http://127.0.0.1:4200` e informe o usuário e a senha de `PREFECT_AUTH_STRING`.

## Teste local

Teste pré-deploy completo, igual ao CI:

```bash
docker build -t mpb-flows:local .
orchestrator/bin/integration-test.sh mpb-flows:local
```

O teste usa o projeto Compose `mpb-prefect` e remove os volumes ao final. Ele
não executa se a stack local já existe.

Stack local para explorar a UI:

```bash
cp orchestrator/.env.example orchestrator/.env   # preencha com valores de teste
docker compose -f orchestrator/docker-compose.yml up -d --build --wait
docker build -t mpb-flows:local .
orchestrator/bin/register.sh mpb-flows:local local
orchestrator/bin/check.sh mpb-flows:local
```

Para apontar o cliente Prefect local para este servidor:

```bash
uv run prefect profile create local
uv run prefect profile use local
uv run prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
uv run prefect config set PREFECT_API_AUTH_STRING=<usuario:senha>
```

Não inicie outro worker na máquina local: o serviço `prefect-worker` já atende o work pool.

## Observações

- Os runners do GitHub geram a imagem para `linux/amd64`. Para uma EC2
  Graviton, gere a imagem para `linux/arm64` no workflow `image.yml`.
- Os containers dos flow runs entram na rede `mpb-prefect` para alcançar a API.
- As versões do Prefect na imagem dos flows, na imagem do servidor, no
  `worker.Dockerfile` e no `uv.lock` devem ser iguais.
