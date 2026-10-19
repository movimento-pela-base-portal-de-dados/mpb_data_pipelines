from pathlib import Path

from mpb_data_pipelines.ops.checks import load_deployment_names

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_prefect_file_declares_healthcheck_deployment() -> None:
    assert "healthcheck" in load_deployment_names(REPO_ROOT / "prefect.yaml")


def test_empty_deployments_list(tmp_path: Path) -> None:
    prefect_file = tmp_path / "prefect.yaml"
    prefect_file.write_text("deployments: []\n")
    assert load_deployment_names(prefect_file) == set()
