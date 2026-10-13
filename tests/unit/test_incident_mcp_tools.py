"""
Unit tests for Incident MCP tools (apps.mcp_incident.tools).
Tests incident creation, lifecycle transitions, evidence sanitization,
hypothesis calibration, action proposals, and event emission offline.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from apps.mcp_incident.models import (
    AddEvidenceInput,
    AddHypothesisInput,
    CloseIncidentInput,
    CreateActionProposalInput,
    CreateIncidentInput,
    GetIncidentInput,
    UpdateIncidentInput,
)
from apps.mcp_incident.storage import InvestigationStorage
from apps.mcp_incident.tools import IncidentTools


@pytest.mark.anyio
async def test_incident_tools_create_and_update():
    events = []
    mock_emitter = AsyncMock(side_effect=lambda topic, payload: events.append((topic, payload)))
    storage = InvestigationStorage()
    tools = IncidentTools(storage=storage, event_emitter=mock_emitter)

    # 1. Create
    inc = await tools.create_incident(
        CreateIncidentInput(
            incident_id="inc-100",
            title="Database pool exhausted",
            service="payment-service",
            severity="SEV-1",
            summary="QueuePool full",
        )
    )
    assert inc["incident_id"] == "inc-100"
    assert inc["status"] == "detected"
    assert len(events) == 1
    assert events[0][0] == "incidents.created"

    # 2. Update status and summary
    updated = await tools.update_incident(
        UpdateIncidentInput(
            incident_id="inc-100",
            status="investigating",
            summary="Agent analyzing logs and db connections",
        )
    )
    assert updated["status"] == "investigating"
    assert "Agent analyzing" in updated["summary"]
    assert len(events) == 2
    assert events[1][0] == "incidents.updated"


@pytest.mark.anyio
async def test_incident_tools_create_invalid_severity():
    tools = IncidentTools()
    with pytest.raises(ValueError, match="Invalid severity"):
        await tools.create_incident(
            CreateIncidentInput(
                title="Bad severity test",
                service="payment-service",
                severity="SEV-99",
            )
        )


@pytest.mark.anyio
async def test_incident_tools_add_evidence_sanitization():
    storage = InvestigationStorage()
    tools = IncidentTools(storage=storage)
    await tools.create_incident(
        CreateIncidentInput(incident_id="inc-200", title="Evidence test", service="payment-service")
    )

    raw_tool_data = {
        "error": "Failed query",
        "db_password": "super_secret_password_123",
        "api_key": "sk-1234567890abcdef",
        "safe_metric": 42,
    }

    evidence = await tools.add_evidence(
        AddEvidenceInput(
            incident_id="inc-200",
            source_tool="mcp_database.run_readonly_query",
            signal_type="pool_exhaustion",
            confidence_weight=0.95,
            raw_data=raw_tool_data,
            interpretation="Connection failure with secret credentials",
        )
    )

    assert evidence["incident_id"] == "inc-200"
    # Ensure sensitive fields were redacted by Sanitizer
    assert evidence["raw_data"]["db_password"] == "[REDACTED]"
    assert evidence["raw_data"]["api_key"] == "[REDACTED]"
    assert evidence["raw_data"]["safe_metric"] == 42


@pytest.mark.anyio
async def test_incident_tools_add_hypothesis_and_event():
    events = []
    mock_emitter = AsyncMock(side_effect=lambda topic, payload: events.append((topic, payload)))
    storage = InvestigationStorage()
    tools = IncidentTools(storage=storage, event_emitter=mock_emitter)
    await tools.create_incident(
        CreateIncidentInput(incident_id="inc-300", title="Hypothesis test", service="payment-service")
    )

    hypo = await tools.add_hypothesis(
        AddHypothesisInput(
            incident_id="inc-300",
            title="v2.8.1 commit c0ffee1 leaks asyncpg connections",
            confidence_score=0.88,
            supporting_evidence=["ev-1"],
            rationale="Unified diff confirms acquire_connection misses conn.close()",
        )
    )

    assert hypo["confidence_score"] == 0.88
    assert hypo["status"] == "active"
    assert len(events) == 2  # create + hypothesis
    assert events[1][0] == "ai.analysis"


@pytest.mark.anyio
async def test_incident_tools_create_action_proposal():
    events = []
    mock_emitter = AsyncMock(side_effect=lambda topic, payload: events.append((topic, payload)))
    storage = InvestigationStorage()
    tools = IncidentTools(storage=storage, event_emitter=mock_emitter)
    await tools.create_incident(
        CreateIncidentInput(incident_id="inc-400", title="Proposal test", service="payment-service")
    )

    proposal = await tools.create_action_proposal(
        CreateActionProposalInput(
            incident_id="inc-400",
            action_type="rollback_deployment",
            parameters={"service": "payment-service", "target_version": "v2.8.0", "admin_token": "topsecret"},
            risk_level="HIGH",
            rationale="Roll back v2.8.1 to resolve pool leak",
        )
    )

    assert proposal["action_type"] == "rollback_deployment"
    assert proposal["risk_level"] == "HIGH"
    assert proposal["parameters"]["admin_token"] == "[REDACTED]"
    assert len(events) == 2
    assert events[1][0] == "ai.actions.proposed"


@pytest.mark.anyio
async def test_incident_tools_close_incident():
    events = []
    mock_emitter = AsyncMock(side_effect=lambda topic, payload: events.append((topic, payload)))
    storage = InvestigationStorage()
    tools = IncidentTools(storage=storage, event_emitter=mock_emitter)
    await tools.create_incident(
        CreateIncidentInput(incident_id="inc-500", title="Close test", service="payment-service")
    )

    hypo = await tools.add_hypothesis(
        AddHypothesisInput(
            incident_id="inc-500",
            title="Winning hypothesis",
            confidence_score=0.9,
        )
    )

    closed = await tools.close_incident(
        CloseIncidentInput(
            incident_id="inc-500",
            root_cause="Connection leak in v2.8.1 commit c0ffee1",
            winning_hypothesis_id=hypo["id"],
            summary="Deployment rolled back to v2.8.0 and pool metrics verified healthy",
        )
    )

    assert closed["status"] == "resolved"
    assert "Root cause" in closed["summary"]
    assert closed["resolved_at"] is not None


@pytest.mark.anyio
async def test_incident_tools_get_incident_consolidated():
    storage = InvestigationStorage()
    tools = IncidentTools(storage=storage)
    await tools.create_incident(
        CreateIncidentInput(incident_id="inc-600", title="Consolidated test", service="payment-service")
    )
    await tools.add_evidence(
        AddEvidenceInput(
            incident_id="inc-600",
            source_tool="test",
            signal_type="log",
            confidence_weight=0.8,
            raw_data={},
            interpretation="Test evidence",
        )
    )
    await tools.add_hypothesis(
        AddHypothesisInput(
            incident_id="inc-600",
            title="Test hypothesis",
            confidence_score=0.7,
        )
    )
    await tools.create_action_proposal(
        CreateActionProposalInput(
            incident_id="inc-600",
            action_type="restart",
            risk_level="MEDIUM",
        )
    )

    details = await tools.get_incident(GetIncidentInput(incident_id="inc-600"))
    assert details["incident_id"] == "inc-600"
    assert len(details["evidence"]) == 1
    assert len(details["hypotheses"]) == 1
    assert len(details["action_proposals"]) == 1
