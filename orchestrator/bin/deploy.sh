#!/usr/bin/env bash
# Deploy na EC2: gera o .env a partir do SSM, atualiza os serviços e registra
# os deployments. Executado pelo CD por SSM Run Command, após o checkout do commit.
# Uso: AWS_REGION=... deploy.sh IMAGEM VERSAO
set -euo pipefail
# shellcheck source=orchestrator/bin/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image=${1:?informe a imagem}
version=${2:?informe a versão}
: "${AWS_REGION:?defina AWS_REGION}"
ssm_path=${MPB_SSM_PATH:-/mpb/prefect/}

echo "gerando $MPB_ENV_FILE a partir de $ssm_path"
(
    umask 077
    aws ssm get-parameters-by-path --region "$AWS_REGION" --path "$ssm_path" \
        --with-decryption --query 'Parameters[].[Name,Value]' --output text |
        while IFS=$'\t' read -r name value; do
            echo "${name##*/}=$value"
        done > "$MPB_ENV_FILE"
)

echo "baixando $image"
aws ecr get-login-password --region "$AWS_REGION" |
    docker login --username AWS --password-stdin "${image%%/*}"
docker pull --quiet "$image"

echo "atualizando os serviços"
compose up -d --build --wait

echo "registrando os deployments"
"$ORCH_DIR/bin/register.sh" "$image" "$version"
