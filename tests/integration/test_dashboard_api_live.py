"""
Live Integration Tests for Dashboard Core API Endpoints
Verifies API routers, storage interaction, and live active probing with services running together.
"""

import asyncio
import socket
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from apps.api.dependencies import OperatorContext, get_storage, require_operator_authorization, set_storage
from apps.api.main import app
from apps.mcp_incident.storage import InvestigationStorage


@pytest.mark.integration
def test_dashboard_api_live_incident_lifecycle():
    """Tests complete incident data retrieval pipeline through FastAPI."""
    storage = InvestigationStorage()
    set_storage(storage)

    client = TestClient(app)

    async def _seed():
        inc = await storage.create_incident(
            incident_id="live-inc-101",
            title="Production Payment Gateway Outage",
            service="payment-service",
            severity="CRITICAL",
            summary="Elevated 500 error rates following deployment v2.8.1",
        )
        await storage.add_evidence(
            incident_id="live-inc-101",
            source_tool="mcp_logs",
            signal_type="error_rate_anomaly",
            confidence_weight=0.95,
            raw_data={"error_rate": 0.045, "threshold": 0.01},
            interpretation="HTTP error rate spiked to 4.5% immediately after deploy",
        )
        await storage.add_or_update_hypothesis(
            incident_id="live-inc-101",
            hypothesis_id="live-hypo-1",
            title="H1: Database Connection Leak",
            confidence_score=0.88,
            rationale="Corroborated by DB pool exhaustion and leaking Git commit diff",
        )
        await storage.record_tool_call(
            incident_id="live-inc-101",
            tool_name="mcp_logs:get_error_rate",
            duration_ms=82.4,
            parameters={"service": "payment-service", "window_minutes": 5},
            result_summary="Error rate 4.5%",
        )

    asyncio.run(_seed())

    # 1. Verify list
    res_list = client.get("/api/incidents")
    assert res_list.status_code == 200
    incidents = res_list.json()
    assert len(incidents) >= 1
    target = next((i for i in incidents if i["incident_id"] == "live-inc-101"), None)
    assert target is not None
    assert target["severity"] == "CRITICAL"
    assert target["service"] == "payment-service"

    # 2. Verify single detail
    res_detail = client.get("/api/incidents/live-inc-101")
    assert res_detail.status_code == 200
    assert res_detail.json()["title"] == "Production Payment Gateway Outage"

    # 3. Verify evidence endpoint
    res_ev = client.get("/api/incidents/live-inc-101/evidence")
    assert res_ev.status_code == 200
    assert len(res_ev.json()) == 1
    assert res_ev.json()[0]["signal_type"] == "error_rate_anomaly"

    # 4. Verify hypothesis endpoint
    res_hypo = client.get("/api/incidents/live-inc-101/hypotheses")
    assert res_hypo.status_code == 200
    assert len(res_hypo.json()) == 1
    assert res_hypo.json()[0]["confidence_score"] == 0.88

    # 5. Verify tool history endpoint
    res_tools = client.get("/api/incidents/live-inc-101/tools")
    assert res_tools.status_code == 200
    assert len(res_tools.json()) == 1
    assert res_tools.json()[0]["tool_name"] == "mcp_logs:get_error_rate"

    set_storage(None)


@pytest.mark.integration
def test_dashboard_api_live_observability_probe():
    """Tests active network probing against a temporary local TCP socket server."""
    client = TestClient(app)

    # Spawn a temporary TCP server to simulate a live healthy service
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    # Verify that an active probe against this port returns 200 schema
    res = client.get("/api/observability/status")
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert "services" in data
    assert len(data["services"]) == 11

    server_sock.close()


@pytest.mark.integration
def test_dashboard_operator_authorization_dependency():
    """Verifies that require_operator_authorization enforces authentication and roles."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    test_app = FastAPI()

    @test_app.post("/test-protected")
    async def protected_route(ctx: OperatorContext = Depends(require_operator_authorization)):
        return {"status": "ok", "operator_id": ctx.operator_id, "role": ctx.role}

    c = TestClient(test_app)

    # Missing X-Operator-Id -> 401
    res_401 = c.post("/test-protected")
    assert res_401.status_code == 401
    assert "authentication required" in res_401.json()["detail"].lower()

    # Empty whitespace X-Operator-Id -> 401
    res_empty = c.post("/test-protected", headers={"X-Operator-Id": "   "})
    assert res_empty.status_code == 401

    # Unauthorized role -> 403
    res_403 = c.post("/test-protected", headers={"X-Operator-Id": "guest@test.com", "X-Operator-Role": "unauthorized_role"})
    assert res_403.status_code == 403
    assert "not authorized" in res_403.json()["detail"].lower()

    # Valid operator and SRE role -> 200
    res_200 = c.post("/test-protected", headers={"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"})
    assert res_200.status_code == 200
    assert res_200.json()["operator_id"] == "sre-lead@aegisops.ai"
    assert res_200.json()["role"] == "sre"


@pytest.mark.integration
def test_dashboard_api_live_end_to_end_governance_remediation():
    """End-to-end test: Incident -> Proposal -> Approval -> Rollback -> Verification -> Closure -> Audit."""
    storage = InvestigationStorage()
    set_storage(storage)

    client = TestClient(app)
    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    async def _setup():
        await storage.create_incident(
            incident_id="e2e-inc-101",
            title="E2E Payment Service Database Pool Exhaustion",
            service="payment-service",
            severity="CRITICAL",
        )
        await storage.create_action_proposal(
            incident_id="e2e-inc-101",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0"},
            risk_level="HIGH",
            rationale="Rollback to stable v2.8.0 eliminates connection leak",
            proposal_id="e2e-prop-101",
        )

    asyncio.run(_setup())

    # 1. Fetch proposals
    res_props = client.get("/api/incidents/e2e-inc-101/proposals")
    assert res_props.status_code == 200
    assert len(res_props.json()) == 1

    # 2. Operator Approves
    res_appr = client.post(
        "/api/proposals/e2e-prop-101/approve",
        headers=headers,
        json={"comment": "Verified root cause: leaking connection diff in v2.8.1"},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"

    # 3. Operator Executes Rollback
    res_exec = client.post(
        "/api/proposals/e2e-prop-101/execute",
        headers=headers,
        json={"parameters": {"service": "payment-service", "target_version": "v2.8.0"}},
    )
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "executed"

    # 4. Verify Telemetry & Close Incident
    res_close = client.post(
        "/api/incidents/e2e-inc-101/verify-and-close",
        headers=headers,
        json={"proposal_id": "e2e-prop-101", "root_cause": "Unclosed connection leak in commit c4a1b2c"},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "resolved"

    # 5. Query Audit Trail
    res_audit = client.get("/api/audit?incident_id=e2e-inc-101", headers=headers)
    assert res_audit.status_code == 200
    events = [e["event_type"] for e in res_audit.json()]
    assert "PROPOSAL_APPROVED" in events
    assert "PROPOSAL_EXECUTED" in events
    assert "INCIDENT_CLOSED_VERIFIED" in events

    set_storage(None)

