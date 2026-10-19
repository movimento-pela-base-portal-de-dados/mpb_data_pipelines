#!/usr/bin/env bash
# Verifica API, work pool, deployments e executa o flow healthcheck.
# Uso: check.sh IMAGEM
set -euo pipefail
# shellcheck source=orchestrator/bin/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image=${1:?informe a imagem}

run_in_flow_image "$image" python -m mpb_data_pipelines.ops.checks --image "$image"
