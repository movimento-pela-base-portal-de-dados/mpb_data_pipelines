# Contratos entre repositórios

## Com mpb-infra
A infraestrutura fornece buckets/prefixos S3, IAM Role/policies, parâmetros/segredos e observabilidade. Pipelines não criam infraestrutura diretamente.

## Com mpb-ckan
A publicação de catálogo ocorre pela API CKAN. O pipeline envia metadados e referências aos recursos publicados; não acopla aquisição e transformação ao processo da aplicação CKAN.

## Contrato inicial de armazenamento
- `raw/`: cópia recebida da fonte, preservada sem transformação semântica.
- `processed/`: dados validados, padronizados e tratados.
- `published/`: artefatos prontos para disponibilização.

Convenções detalhadas de paths, schemas, particionamento e versionamento serão definidas conforme os primeiros conjuntos de dados forem implementados.
