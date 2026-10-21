# Contratos entre repositórios

## Com mpb-infra
A infraestrutura fornece buckets/prefixos S3, IAM Role/policies, parâmetros/segredos e observabilidade. Pipelines não criam infraestrutura diretamente.

Para a EC2 do orquestrador (veja `orchestrator/README.md`), o mpb-infra fornece:
- EC2 com Docker, plugin Compose, `git`, `jq`, AWS CLI e agente SSM, e disco EBS para o Postgres do Prefect.
- Clone do repositório em `/opt/mpb_data_pipelines`, de propriedade do root (o SSM executa como root), e o diretório `/var/lib/mpb-prefect/`.
- Repositório ECR para a imagem dos flows, com tags imutáveis e lifecycle policy que expira imagens `tree-*` antigas.
- Instance role com pull no ECR e `ssm:GetParametersByPath` em `/mpb/prefect/*`. O acesso ao S3 entra com os primeiros flows reais.
- IMDSv2 com hop limit 2, para que os containers usem as credenciais da instance role.
- Security group sem acesso público à porta `4200`. O acesso é pelo SSM.
- Valores do `orchestrator/.env` no SSM Parameter Store, em `/mpb/prefect/<CHAVE>` (por exemplo, `/mpb/prefect/POSTGRES_PASSWORD`).

Para o CI/CD (veja `docs/adr/0002-ci-cd.md`), o mpb-infra fornece:
- Provedor OIDC do GitHub (`token.actions.githubusercontent.com`) na conta AWS.
- Role `mpb-data-pipelines-ci`: confia em `repo:movimento-pela-base-portal-de-dados/mpb_data_pipelines:pull_request`; permite apenas push e leitura no repositório ECR.
- Role `mpb-data-pipelines-cd`: confia em `repo:movimento-pela-base-portal-de-dados/mpb_data_pipelines:environment:production` e `...:ref:refs/heads/main` (build de fallback); permite push e leitura no ECR, `ssm:SendCommand` na instância do orquestrador com o documento `AWS-RunShellScript` e `ssm:GetCommandInvocation`.

## Com mpb-ckan
A publicação de catálogo ocorre pela API CKAN. O pipeline envia metadados e referências aos recursos publicados; não acopla aquisição e transformação ao processo da aplicação CKAN.

Os mapeamentos entre fontes e campos CKAN ficam em `src/mpb_data_pipelines/schemas/`:
- `pesquisa.yaml`: planilha de pesquisas (aba `Metadados`) para o tipo de dataset `pesquisa`.

Cada `field_name` de destino `dataset` ou `resource` precisa existir no schema scheming do mpb-ckan. Uma mudança de campo exige mudança nos dois repositórios. `load_mapping` valida o arquivo: colunas sem repetição, choices dos aliases, recursos conhecidos e os campos que o mpb-ckan exige (`title`, `name`, `tag_string`, `owner_org`).

## Contrato inicial de armazenamento
- `raw/`: cópia recebida da fonte, preservada sem transformação semântica.
- `processed/`: dados validados, padronizados e tratados.
- `published/`: artefatos prontos para disponibilização.

Convenções detalhadas de paths, schemas, particionamento e versionamento serão definidas conforme os primeiros conjuntos de dados forem implementados.
