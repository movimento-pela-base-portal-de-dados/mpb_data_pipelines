"""Verificações do orquestrador, executadas no CI (pré-deploy) e na EC2 (pós-deploy).

Uso: python -m mpb_data_pipelines.ops.checks --image <imagem>
"""

import argparse
import sys
import time
from pathlib import Path

import yaml
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import DeploymentFilter, DeploymentFilterName
from prefect.client.schemas.objects import WorkPoolStatus
from prefect.deployments import run_deployment

WORK_POOL = "mpb-docker"
HEALTHCHECK_DEPLOYMENT = "healthcheck/healthcheck"


class CheckError(Exception):
    pass


def load_deployment_names(prefect_file: Path) -> set[str]:
    config = yaml.safe_load(prefect_file.read_text())
    return {deployment["name"] for deployment in config.get("deployments") or []}


def check_api(client) -> None:
    error = client.api_healthcheck()
    if error is not None:
        raise CheckError(f"API indisponível: {error}")


def check_work_pool(client, wait_seconds: float) -> None:
    deadline = time.monotonic() + wait_seconds
    while True:
        status = client.read_work_pool(WORK_POOL).status
        if status == WorkPoolStatus.READY:
            return
        if time.monotonic() >= deadline:
            raise CheckError(f"work pool {WORK_POOL} sem worker online (status: {status})")
        time.sleep(5)


def check_deployments(client, names: set[str], image: str) -> None:
    deployments = client.read_deployments(
        deployment_filter=DeploymentFilter(name=DeploymentFilterName(any_=sorted(names)))
    )
    found = {deployment.name for deployment in deployments}
    if missing := names - found:
        raise CheckError(f"deployments ausentes: {sorted(missing)}")
    for deployment in deployments:
        current = (deployment.job_variables or {}).get("image")
        if current != image:
            raise CheckError(f"deployment {deployment.name} usa a imagem {current}, não {image}")


def check_healthcheck_run(timeout: float) -> None:
    flow_run = run_deployment(HEALTHCHECK_DEPLOYMENT, timeout=timeout, as_subflow=False)
    if flow_run.state is None or not flow_run.state.is_completed():
        raise CheckError(f"flow run {flow_run.name} terminou em {flow_run.state}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="imagem esperada nos deployments")
    parser.add_argument("--prefect-file", type=Path, default=Path("prefect.yaml"))
    parser.add_argument("--worker-wait", type=float, default=120)
    parser.add_argument("--run-timeout", type=float, default=600)
    args = parser.parse_args(argv)

    try:
        with get_client(sync_client=True) as client:
            print("verificando a API...")
            check_api(client)
            print(f"verificando o work pool {WORK_POOL}...")
            check_work_pool(client, args.worker_wait)
            print("verificando os deployments...")
            check_deployments(client, load_deployment_names(args.prefect_file), args.image)
        print(f"executando {HEALTHCHECK_DEPLOYMENT}...")
        check_healthcheck_run(args.run_timeout)
    except CheckError as error:
        print(f"FALHA: {error}", file=sys.stderr)
        return 1
    print("todas as verificações passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
