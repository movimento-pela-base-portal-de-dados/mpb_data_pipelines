#!/usr/bin/env bash
# Registra os deployments do prefect.yaml com a própria imagem dos flows.
# Uso: register.sh IMAGEM VERSAO
set -euo pipefail
# shellcheck source=orchestrator/bin/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image=${1:?informe a imagem}
version=${2:?informe a versão}

run_in_flow_image -e MPB_FLOW_IMAGE="$image" -e MPB_VERSION="$version" \
    "$image" prefect --no-prompt deploy --all
