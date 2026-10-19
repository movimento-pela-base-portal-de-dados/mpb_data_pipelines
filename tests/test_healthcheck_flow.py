from prefect.testing.utilities import prefect_test_harness

from mpb_data_pipelines.flows.healthcheck import healthcheck


def test_healthcheck_flow_returns_ok() -> None:
    with prefect_test_harness():
        assert healthcheck() == "ok"
