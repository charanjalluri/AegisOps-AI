"""
AegisOps AI - End-to-End Incident Demo Integration Tests (DEMO-02, DEMO-03)
Tests end-to-end closed loop demo execution across scenarios:
failure injection -> autonomous LangGraph investigation -> RCA synthesis ->
HITL approval -> remediation execution -> verification -> incident closure.
"""

import pytest

from scripts.run_demo import run_demo
from scripts.reset_demo import reset_demo_async


@pytest.mark.integration
@pytest.mark.anyio
async def test_end_to_end_demo_flagship_scenario():
    """Validates the complete closed loop demo run for database-connection-leak."""
    exit_code = await run_demo(
        scenario_id="database-connection-leak",
        auto_approve=True,
        standalone=True,
    )
    assert exit_code == 0, "Flagship demo run must terminate with success exit code 0"

    # Reset demo state after run
    await reset_demo_async()


@pytest.mark.integration
@pytest.mark.anyio
async def test_end_to_end_demo_bad_deployment_scenario():
    """Validates end-to-end closed loop demo run on bad-deployment benchmark scenario."""
    exit_code = await run_demo(
        scenario_id="bad-deployment",
        auto_approve=True,
        standalone=True,
    )
    assert exit_code == 0, "Bad deployment demo run must terminate with success exit code 0"

    # Reset demo state after run
    await reset_demo_async()
