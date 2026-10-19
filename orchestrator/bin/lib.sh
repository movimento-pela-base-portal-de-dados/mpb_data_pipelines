# shellcheck shell=bash
# Funções comuns dos scripts do orquestrador. Use com `source`.

ORCH_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MPB_ENV_FILE=${MPB_ENV_FILE:-$ORCH_DIR/.env}
PREFECT_NETWORK=mpb-prefect
PREFECT_INTERNAL_API_URL=http://prefect-server:4200/api

env_value() {
    grep -E "^$1=" "$MPB_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

compose() {
    docker compose -f "$ORCH_DIR/docker-compose.yml" --env-file "$MPB_ENV_FILE" "$@"
}

# Executa um comando em um container da imagem dos flows, na rede do servidor Prefect.
# Uso: run_in_flow_image [opções do docker run] IMAGEM COMANDO...
run_in_flow_image() {
    docker run --rm --network "$PREFECT_NETWORK" \
        -e PREFECT_API_URL="$PREFECT_INTERNAL_API_URL" \
        -e PREFECT_API_AUTH_STRING="$(env_value PREFECT_AUTH_STRING)" \
        "$@"
}
