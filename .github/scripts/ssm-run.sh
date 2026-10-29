#!/usr/bin/env bash
# Executa um comando shell na EC2 do orquestrador por SSM Run Command, espera o
# fim, mostra a saída e sai com o status do comando.
# Uso: ORCHESTRATOR_INSTANCE_ID=... AWS_REGION=... ssm-run.sh DESCRICAO COMANDO
set -euo pipefail

description=${1:?informe a descrição}
command=${2:?informe o comando}
: "${ORCHESTRATOR_INSTANCE_ID:?defina ORCHESTRATOR_INSTANCE_ID}"
timeout_seconds=${SSM_TIMEOUT_SECONDS:-1800}

# O SSM executa como root, sem HOME definido; git e docker precisam dele.
parameters=$(jq -n --arg command "export HOME=/root; set -e; $command" \
    --arg timeout "$timeout_seconds" \
    '{commands: [$command], executionTimeout: [$timeout]}')

command_id=$(aws ssm send-command \
    --instance-ids "$ORCHESTRATOR_INSTANCE_ID" \
    --document-name AWS-RunShellScript \
    --comment "mpb-data-pipelines: $description" \
    --parameters "$parameters" \
    --query Command.CommandId --output text)
echo "SSM command $command_id ($description)"

deadline=$((SECONDS + timeout_seconds + 60))
status=Pending
while [ "$SECONDS" -lt "$deadline" ]; do
    sleep 10
    status=$(aws ssm get-command-invocation \
        --command-id "$command_id" --instance-id "$ORCHESTRATOR_INSTANCE_ID" \
        --query Status --output text 2>/dev/null || echo Pending)
    case $status in
        Pending | InProgress | Delayed) continue ;;
        *) break ;;
    esac
done

aws ssm get-command-invocation \
    --command-id "$command_id" --instance-id "$ORCHESTRATOR_INSTANCE_ID" \
    --query '[StandardOutputContent, StandardErrorContent]' --output text || true

echo "status: $status"
[ "$status" = Success ]
