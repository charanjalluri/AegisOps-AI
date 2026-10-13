"""
Unit tests for Governance REST API Router (/api/proposals, /api/audit, verify-and-close)
Verifies server-side authorization, parameter binding, TTL expiration, and replay prevention.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from apps.api.dependencies import set_storage
from apps.api.main import app
from apps.api.routers.governance import (
    APPROVAL_TTL_SECONDS,
    _approval_bindings,
    clear_approval_bindings,
    set_governance_services_override,
)
from apps.mcp_incident.storage import InvestigationStorage


@pytest.fixture(autouse=True)
def clean_governance_env():
    storage = InvestigationStorage()
    set_storage(storage)
    clear_approval_bindings()
    set_governance_services_override(None, None, None, None, None)
    yield storage
    clear_approval_bindings()
    set_storage(None)
    set_governance_services_override(None, None, None, None, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_approve_requires_operator_authorization(client, clean_governance_env):
    """Verifies that approve endpoint mandates server-side operator authentication."""
    storage = clean_governance_env
    # Seed proposal
    prop = pytest.helpers_seed_proposal(storage, "prop-auth-1", "inc-1") if hasattr(pytest, "helpers_seed_proposal") else None

    # 1. Missing X-Operator-Id -> 401
    res_401 = client.post("/api/proposals/prop-auth-1/approve", json={"comment": "LGTM"})
    assert res_401.status_code == 401
    assert "authentication required" in res_401.json()["detail"].lower()

    # 2. Empty whitespace X-Operator-Id -> 401
    res_empty = client.post(
        "/api/proposals/prop-auth-1/approve",
        headers={"X-Operator-Id": "   "},
        json={"comment": "LGTM"},
    )
    assert res_empty.status_code == 401

    # 3. Unauthorized role -> 403
    res_403 = client.post(
        "/api/proposals/prop-auth-1/approve",
        headers={"X-Operator-Id": "guest@test.com", "X-Operator-Role": "unauthorized"},
        json={"comment": "LGTM"},
    )
    assert res_403.status_code == 403


def test_proposal_lifecycle_approve_and_reject(client, clean_governance_env):
    storage = clean_governance_env
    import asyncio

    async def _seed():
        await storage.create_incident("inc-gov-1", "Payment Pool Exhaustion", "payment-service")
        await storage.create_action_proposal(
            incident_id="inc-gov-1",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0"},
            risk_level="HIGH",
            rationale="Revert leaking connection pool commit",
            proposal_id="prop-test-1",
        )
        await storage.create_action_proposal(
            incident_id="inc-gov-1",
            action_type="restart_service",
            parameters={"service": "payment-service"},
            risk_level="MEDIUM",
            rationale="Temporary restart",
            proposal_id="prop-test-2",
        )

    asyncio.run(_seed())

    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    # 1. Fetch proposals
    res_list = client.get("/api/incidents/inc-gov-1/proposals")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2

    # 2. Approve proposal 1
    res_appr = client.post(
        "/api/proposals/prop-test-1/approve",
        headers=headers,
        json={"comment": "Approved following code diff verification"},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"
    assert res_appr.json()["approved_by"] == "sre-lead@aegisops.ai"

    # Cannot re-approve an already approved proposal
    res_reappr = client.post(
        "/api/proposals/prop-test-1/approve",
        headers=headers,
        json={"comment": "Second approve"},
    )
    assert res_reappr.status_code == 400

    # 3. Reject proposal 2
    res_rej = client.post(
        "/api/proposals/prop-test-2/reject",
        headers=headers,
        json={"reason": "Restart does not address root cause leak"},
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"


def test_execution_parameter_binding_and_tampering(client, clean_governance_env):
    """Verifies that execution strictly matches approved parameters and rejects tampering."""
    storage = clean_governance_env
    import asyncio

    async def _seed():
        await storage.create_incident("inc-gov-2", "Payment Leak", "payment-service")
        await storage.create_action_proposal(
            incident_id="inc-gov-2",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0"},
            risk_level="HIGH",
            proposal_id="prop-tamper-1",
        )

    asyncio.run(_seed())

    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    # Approve first
    client.post("/api/proposals/prop-tamper-1/approve", headers=headers, json={"comment": "Approved"})

    # Caller attempts to tamper with target_version (v2.7.0 instead of approved v2.8.0)
    res_tamper = client.post(
        "/api/proposals/prop-tamper-1/execute",
        headers=headers,
        json={"parameters": {"service": "payment-service", "target_version": "v2.7.0"}},
    )
    assert res_tamper.status_code == 400
    assert "tampering detected" in res_tamper.json()["detail"].lower()


def test_execution_replay_prevention(client, clean_governance_env):
    """Verifies that an executed proposal cannot be executed again (replay attack prevention)."""
    storage = clean_governance_env
    import asyncio

    async def _seed():
        await storage.create_incident("inc-gov-3", "Payment Leak", "payment-service")
        await storage.create_action_proposal(
            incident_id="inc-gov-3",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0"},
            risk_level="HIGH",
            proposal_id="prop-replay-1",
        )

    asyncio.run(_seed())

    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    # 1. Approve
    client.post("/api/proposals/prop-replay-1/approve", headers=headers, json={"comment": "Approved"})

    # 2. First Execution -> 200 OK
    res_exec1 = client.post(
        "/api/proposals/prop-replay-1/execute",
        headers=headers,
        json={"parameters": {"service": "payment-service", "target_version": "v2.8.0"}},
    )
    assert res_exec1.status_code == 200
    assert res_exec1.json()["status"] == "executed"

    # 3. Second Execution -> 409 Conflict Replay Rejection
    res_exec2 = client.post(
        "/api/proposals/prop-replay-1/execute",
        headers=headers,
        json={"parameters": {"service": "payment-service", "target_version": "v2.8.0"}},
    )
    assert res_exec2.status_code == 409
    assert "already executed" in res_exec2.json()["detail"].lower()


def test_execution_ttl_expiration(client, clean_governance_env):
    """Verifies that an approval older than TTL window (30m) expires and cannot execute."""
    storage = clean_governance_env
    import asyncio

    async def _seed():
        await storage.create_incident("inc-gov-4", "Payment Leak", "payment-service")
        await storage.create_action_proposal(
            incident_id="inc-gov-4",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0"},
            risk_level="HIGH",
            proposal_id="prop-ttl-1",
        )

    asyncio.run(_seed())

    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    # Approve
    client.post("/api/proposals/prop-ttl-1/approve", headers=headers, json={"comment": "Approved"})

    # Simulate TTL expiration by modifying approved_at timestamp in binding to 31 minutes ago
    _approval_bindings["prop-ttl-1"]["approved_at"] = datetime.now(timezone.utc) - timedelta(seconds=APPROVAL_TTL_SECONDS + 60)

    # Attempt to execute expired proposal -> 409 Conflict
    res_expired = client.post("/api/proposals/prop-ttl-1/execute", headers=headers, json={})
    assert res_expired.status_code == 409
    assert "expired" in res_expired.json()["detail"].lower()


def test_verification_status_and_closure(client, clean_governance_env):
    storage = clean_governance_env
    import asyncio

    async def _seed():
        await storage.create_incident("inc-gov-5", "Payment Leak", "payment-service")
        await storage.create_action_proposal(
            incident_id="inc-gov-5",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0"},
            risk_level="HIGH",
            proposal_id="prop-close-1",
        )

    asyncio.run(_seed())

    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    # 1. Query verification status while active
    res_status = client.get("/api/incidents/inc-gov-5/verification-status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "in_progress"
    assert len(res_status.json()["conditions"]) == 2

    # 2. Execute verify and close
    res_close = client.post(
        "/api/incidents/inc-gov-5/verify-and-close",
        headers=headers,
        json={"proposal_id": "prop-close-1", "root_cause": "Unclosed connection leak"},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "resolved"

    # 3. Query verification status after closure
    res_after = client.get("/api/incidents/inc-gov-5/verification-status")
    assert res_after.status_code == 200
    assert res_after.json()["status"] == "verified"


def test_audit_trail_requires_authorization_and_returns_entries(client, clean_governance_env):
    """Verifies that audit endpoint requires authorization and returns immutable records."""
    headers = {"X-Operator-Id": "sre-lead@aegisops.ai", "X-Operator-Role": "sre"}

    # Unauthenticated -> 401
    assert client.get("/api/audit").status_code == 401

    # Authenticated -> 200
    res = client.get("/api/audit", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
