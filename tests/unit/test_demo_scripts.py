import asyncio
from unittest.mock import patch
import pytest

from scripts.run_demo import run_demo
from scripts.reset_demo import reset_demo_async, reset_demo_database, reset_test_incidents, reset_payment_simulator


@pytest.mark.anyio
async def test_run_demo_standalone_auto_approve():
    """Verify run_demo completes successfully in standalone mode with auto-approval."""
    exit_code = await run_demo(
        scenario_id="database-connection-leak",
        auto_approve=True,
        standalone=True,
    )
    assert exit_code == 0, "run_demo must return 0 upon successful autonomous execution"


@pytest.mark.anyio
async def test_run_demo_operator_rejection():
    """Verify run_demo halts gracefully with return code 1 if operator rejects the prompt."""
    with patch("builtins.input", return_value="n"):
        exit_code = await run_demo(
            scenario_id="database-connection-leak",
            auto_approve=False,
            standalone=True,
        )
        assert exit_code == 1, "run_demo must return 1 when operator rejects proposal"


@pytest.mark.anyio
async def test_reset_demo_idempotence():
    """Verify reset_demo_async runs cleanly without errors even in offline/mock environment."""
    # Should not raise any unhandled exceptions
    await reset_demo_async()


@pytest.mark.anyio
async def test_reset_helpers_failover():
    """Verify individual reset helpers handle connection failures gracefully."""
    # When DB is offline, reset helpers return False or None without crashing
    db_res = await reset_demo_database()
    assert isinstance(db_res, bool)

    inc_res = await reset_test_incidents()
    assert isinstance(inc_res, bool)

    sim_res = await reset_payment_simulator()
    assert isinstance(sim_res, bool)


def test_prometheus_grafana_configs():
    """Verify Prometheus alert rules and Grafana dashboard configs exist and are valid syntax."""
    import json
    import os
    import yaml

    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Check alert rules
    rules_path = os.path.join(proj_root, "infrastructure", "prometheus", "alert_rules.yml")
    assert os.path.exists(rules_path), "alert_rules.yml must exist"
    with open(rules_path, "r", encoding="utf-8") as f:
        rules_data = yaml.safe_load(f)
    assert "groups" in rules_data

    # Check Grafana dashboard
    dashboard_path = os.path.join(proj_root, "infrastructure", "grafana", "dashboards", "aegisops_incident_dashboard.json")
    assert os.path.exists(dashboard_path), "aegisops_incident_dashboard.json must exist"
    with open(dashboard_path, "r", encoding="utf-8") as f:
        dash_data = json.load(f)
    assert "panels" in dash_data

