#!/usr/bin/env bash
# Teste pré-deploy: sobe a stack com valores de teste, registra os deployments
# e executa as verificações. Remove a stack ao final.
# Uso: integration-test.sh IMAGEM
set -euo pipefail

image=${1:?informe a imagem}

# O teste usa o mesmo projeto Compose da stack local e remove os volumes ao final.
project_filter=label=com.docker.compose.project=mpb-prefect
if [ -n "$(docker ps -aq --filter "$project_filter")$(docker volume ls -q --filter "$project_filter")" ]; then
    echo "a stack mpb-prefect já existe; remova-a antes do teste:" >&2
    echo "  docker compose -p mpb-prefect down -v" >&2
    exit 1
fi

MPB_ENV_FILE=$(mktemp)
export MPB_ENV_FILE
# shellcheck source=orchestrator/bin/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

cat > "$MPB_ENV_FILE" <<ENV
POSTGRES_USER=prefect
POSTGRES_PASSWORD=integration
POSTGRES_DB=prefect
PREFECT_AUTH_STRING=admin:integration
AWS_REGION=us-east-1
ENV

cleanup() {
    local status=$?
    if [ "$status" -ne 0 ]; then
        compose logs --tail 100 prefect-server prefect-worker || true
    fi
    compose down -v --remove-orphans || true
    rm -f "$MPB_ENV_FILE"
    exit "$status"
}
trap cleanup EXIT

compose up -d --build --wait
"$ORCH_DIR/bin/register.sh" "$image" integration
"$ORCH_DIR/bin/check.sh" "$image"
