"""
Unit tests for Incidents REST API Router (/api/incidents)
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from apps.api.dependencies import get_storage, set_storage
from apps.api.main import app
from apps.mcp_incident.storage import InvestigationStorage


@pytest.fixture(autouse=True)
def isolated_storage():
    """Sets a clean in-memory InvestigationStorage for each test."""
    storage = InvestigationStorage()
    set_storage(storage)
    yield storage
    set_storage(None)


@pytest.fixture
def client():
    return TestClient(app)


def test_list_incidents_empty(client):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert response.json() == []


def test_list_incidents_filtering_and_pagination(client, isolated_storage):
    async def _seed():
        await isolated_storage.create_incident(
            incident_id="inc-001",
            title="Payment Service DB Pool Leak",
            service="payment-service",
            severity="CRITICAL",
        )
        await isolated_storage.create_incident(
            incident_id="inc-002",
            title="Order Gateway Latency Spike",
            service="order-service",
            severity="HIGH",
        )
        await isolated_storage.create_incident(
            incident_id="inc-003",
            title="Inventory Sync Delay",
            service="inventory-service",
            severity="MEDIUM",
        )
        await isolated_storage.update_incident(incident_id="inc-003", status="resolved")

    asyncio.run(_seed())

    # 1. List all
    res = client.get("/api/incidents")
    assert res.status_code == 200
    assert len(res.json()) == 3

    # 2. Filter by status
    res = client.get("/api/incidents?status=resolved")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["incident_id"] == "inc-003"

    # 3. Filter by severity
    res = client.get("/api/incidents?severity=CRITICAL")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["incident_id"] == "inc-001"

    # 4. Limit pagination
    res = client.get("/api/incidents?limit=2")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_incident_detail_and_404(client, isolated_storage):
    asyncio.run(
        isolated_storage.create_incident(
            incident_id="inc-100",
            title="Database Deadlock Anomaly",
            service="payment-service",
            severity="HIGH",
        )
    )

    # Valid get
    res = client.get("/api/incidents/inc-100")
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == "inc-100"
    assert data["title"] == "Database Deadlock Anomaly"

    # 404 for unknown
    res_404 = client.get("/api/incidents/unknown-999")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_get_incident_evidence(client, isolated_storage):
    async def _seed():
        await isolated_storage.create_incident(
            incident_id="inc-200",
            title="Connection Pool Saturation",
            service="payment-service",
        )
        await isolated_storage.add_evidence(
            incident_id="inc-200",
            source_tool="mcp_database",
            signal_type="pool_exhaustion",
            confidence_weight=0.92,
            raw_data={"active_connections": 100, "pool_size": 100},
            interpretation="Connection pool capacity completely exhausted",
        )

    asyncio.run(_seed())

    res = client.get("/api/incidents/inc-200/evidence")
    assert res.status_code == 200
    evidence = res.json()
    assert len(evidence) == 1
    assert evidence[0]["source_tool"] == "mcp_database"
    assert evidence[0]["signal_type"] == "pool_exhaustion"
    assert evidence[0]["confidence_weight"] == 0.92

    # 404 on non-existent incident
    res_404 = client.get("/api/incidents/inc-none/evidence")
    assert res_404.status_code == 404


def test_get_incident_hypotheses_sorted(client, isolated_storage):
    async def _seed():
        await isolated_storage.create_incident(
            incident_id="inc-300",
            title="Payment Latency Anomaly",
            service="payment-service",
        )
        await isolated_storage.add_or_update_hypothesis(
            incident_id="inc-300",
            hypothesis_id="hypo-1",
            title="H1: Traffic Surge",
            confidence_score=0.25,
            rationale="Organic spike",
        )
        await isolated_storage.add_or_update_hypothesis(
            incident_id="inc-300",
            hypothesis_id="hypo-2",
            title="H2: Connection Leak",
            confidence_score=0.88,
            rationale="Corroborated by DB and Git",
        )

    asyncio.run(_seed())

    res = client.get("/api/incidents/inc-300/hypotheses")
    assert res.status_code == 200
    hypos = res.json()
    assert len(hypos) == 2
    # Must be sorted descending by confidence_score
    assert hypos[0]["id"] == "hypo-2"
    assert hypos[0]["confidence_score"] == 0.88
    assert hypos[1]["id"] == "hypo-1"
    assert hypos[1]["confidence_score"] == 0.25

    # 404 on non-existent incident
    assert client.get("/api/incidents/missing/hypotheses").status_code == 404


def test_get_incident_tools(client, isolated_storage):
    async def _seed():
        await isolated_storage.create_incident(
            incident_id="inc-400",
            title="Git commit correlation",
            service="payment-service",
        )
        await isolated_storage.record_tool_call(
            incident_id="inc-400",
            tool_name="mcp_github:get_commit",
            duration_ms=45.2,
            parameters={"commit_sha": "c4a1b2c"},
            result_summary="Identified leaking connection diff in payment_handler.go",
        )

    asyncio.run(_seed())

    res = client.get("/api/incidents/inc-400/tools")
    assert res.status_code == 200
    tools = res.json()
    assert len(tools) == 1
    assert tools[0]["tool_name"] == "mcp_github:get_commit"
    assert tools[0]["duration_ms"] == 45.2

    # 404 on non-existent incident
    assert client.get("/api/incidents/missing/tools").status_code == 404
