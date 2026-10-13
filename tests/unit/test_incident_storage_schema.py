"""
Unit tests for short-term investigation memory schema (MEM-01) and storage.
Verifies DDL structure, relational integrity, and in-memory transactional storage operations.
"""

from pathlib import Path
import pytest
from apps.mcp_incident.storage import InvestigationStorage


def test_investigation_schema_sql_content():
    schema_path = Path("infrastructure/postgres/investigation_schema.sql")
    assert schema_path.exists()
    content = schema_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS incident_evidence" in content
    assert "CREATE TABLE IF NOT EXISTS incident_hypotheses" in content
    assert "CREATE TABLE IF NOT EXISTS action_proposals" in content
    assert "CREATE TABLE IF NOT EXISTS investigation_tool_history" in content
    assert "REFERENCES incidents(incident_id)" in content
    assert "ON DELETE CASCADE" in content


@pytest.mark.anyio
async def test_storage_incident_lifecycle():
    storage = InvestigationStorage()
    inc = await storage.create_incident(
        incident_id="inc-test-01",
        title="High error rate on payment-service",
        service="payment-service",
        severity="SEV-1",
        summary="Initial anomaly detected",
    )
    assert inc.incident_id == "inc-test-01"
    assert inc.status == "detected"
    assert inc.severity == "SEV-1"

    fetched = await storage.get_incident("inc-test-01")
    assert fetched is not None
    assert fetched.title == "High error rate on payment-service"

    updated = await storage.update_incident(
        incident_id="inc-test-01",
        status="investigating",
        summary="Agent investigating database connections",
    )
    assert updated.status == "investigating"
    assert "database connections" in updated.summary


@pytest.mark.anyio
async def test_storage_evidence_chaining():
    storage = InvestigationStorage()
    await storage.create_incident("inc-test-02", "DB Connection Pool Exhaustion", "payment-service")

    ev1 = await storage.add_evidence(
        incident_id="inc-test-02",
        source_tool="mcp_logs.search_logs",
        signal_type="log_anomaly",
        confidence_weight=0.9,
        raw_data={"error": "QueuePool limit of size 5 reached"},
        interpretation="Connection pool exhausted in payment-service container",
    )
    assert ev1.incident_id == "inc-test-02"
    assert ev1.confidence_weight == 0.9

    ev2 = await storage.add_evidence(
        incident_id="inc-test-02",
        source_tool="mcp_database.get_connection_pool",
        signal_type="pool_exhaustion",
        confidence_weight=0.95,
        raw_data={"active": 50, "max": 50, "utilization_percent": 100.0},
        interpretation="demo_payment_db connection pool at 100% capacity",
    )

    evidence_list = await storage.get_evidence("inc-test-02")
    assert len(evidence_list) == 2
    assert evidence_list[0].id == ev1.id
    assert evidence_list[1].id == ev2.id


@pytest.mark.anyio
async def test_storage_competing_hypotheses_and_closure():
    storage = InvestigationStorage()
    await storage.create_incident("inc-test-03", "Payment latency spike", "payment-service")

    # Hypothesis 1: Connection pool leak in v2.8.1
    h1 = await storage.add_or_update_hypothesis(
        incident_id="inc-test-03",
        title="v2.8.1 commit c0ffee1 leaks asyncpg connections without closing",
        confidence_score=0.85,
        supporting_evidence=["ev-1", "ev-2"],
        rationale="Code diff in c0ffee1 shows acquire_connection bypasses pool without close()",
    )
    assert h1.status == "active"
    assert h1.confidence_score == 0.85

    # Hypothesis 2: Traffic surge
    h2 = await storage.add_or_update_hypothesis(
        incident_id="inc-test-03",
        title="Sudden 10x traffic spike from external gateway",
        confidence_score=0.15,
        refuting_evidence=["ev-3"],
        rationale="Request rate metrics remained constant at 45 rps",
    )

    hypotheses = await storage.get_hypotheses("inc-test-03")
    assert len(hypotheses) == 2

    # Close incident validating winning hypothesis
    closed = await storage.close_incident(
        incident_id="inc-test-03",
        root_cause="Connection leak in v2.8.1 commit c0ffee1",
        winning_hypothesis_id=h1.id,
        summary="Rollback to v2.8.0 executed and verified",
    )
    assert closed.status == "resolved"
    assert closed.resolved_at is not None
    assert "Root cause" in closed.summary

    # Verify winning hypothesis was validated
    updated_hypotheses = await storage.get_hypotheses("inc-test-03")
    winning = next(h for h in updated_hypotheses if h.id == h1.id)
    assert winning.status == "validated"
    assert winning.confidence_score == 1.0


@pytest.mark.anyio
async def test_storage_action_proposals_and_tool_history():
    storage = InvestigationStorage()
    await storage.create_incident("inc-test-04", "DB issue", "payment-service")

    proposal = await storage.create_action_proposal(
        incident_id="inc-test-04",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
        rationale="Roll back faulty v2.8.1 deployment to restore connection pool stability",
    )
    assert proposal.status == "proposed"
    assert proposal.risk_level == "HIGH"

    proposals = await storage.get_action_proposals("inc-test-04")
    assert len(proposals) == 1
    assert proposals[0].action_type == "rollback_deployment"

    tool_log = await storage.record_tool_history(
        incident_id="inc-test-04",
        tool_name="mcp_database.get_slow_queries",
        caller="investigation_agent",
        arguments={"min_duration_ms": 100},
        duration_ms=45.2,
        status="success",
        result_summary="Found 2 slow queries",
    )
    assert tool_log.tool_name == "mcp_database.get_slow_queries"

    history = await storage.get_tool_history("inc-test-04")
    assert len(history) == 1
    assert history[0].status == "success"
