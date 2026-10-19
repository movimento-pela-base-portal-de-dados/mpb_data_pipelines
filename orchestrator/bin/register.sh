#!/usr/bin/env bash
# Registra os deployments do prefect.yaml com a própria imagem dos flows.
# Uso: register.sh IMAGEM VERSAO
set -euo pipefail
# shellcheck source=orchestrator/bin/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image=${1:?informe a imagem}
version=${2:?informe a versão}

# O worker cria o work pool ao iniciar, mas pode ainda não ter feito isso quando
# o deploy roda. Sem o pool, o `prefect deploy --no-prompt` falha.
run_in_flow_image -e MPB_FLOW_IMAGE="$image" -e MPB_VERSION="$version" \
    "$image" sh -c "prefect work-pool inspect $WORK_POOL >/dev/null 2>&1 \
        || prefect work-pool create $WORK_POOL --type docker; \
        prefect --no-prompt deploy --all"
