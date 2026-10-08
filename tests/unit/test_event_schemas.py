import json
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from apps.common.schemas.events import (
    RawLogEvent,
    RawMetricEvent,
    DeploymentEvent,
    AlertEvent,
    IncidentEvent,
    AIActionEvent,
    LogLevel,
    RiskLevel,
    IncidentSeverity,
    IncidentStatus,
    ActionStatus,
)

def test_raw_log_event_valid():
    event = RawLogEvent(
        service="payment-service",
        level=LogLevel.ERROR,
        message="Database connection timeout",
        environment="production",
        trace_id="trace-12345",
        metadata={"query": "SELECT * FROM payments", "timeout_ms": 5000},
    )
    json_data = event.model_dump_json()
    data = json.loads(json_data)
    assert data["service"] == "payment-service"
    assert data["level"] == "ERROR"
    assert data["metadata"]["timeout_ms"] == 5000
    assert "event_id" in data
    assert "timestamp" in data

def test_raw_log_event_missing_required_fields():
    with pytest.raises(ValidationError):
        RawLogEvent()  # Missing service and message

def test_raw_metric_event_valid():
    event = RawMetricEvent(
        service="payment-service",
        metric_name="db_pool_utilization",
        value=100.0,
        unit="percent",
        dimensions={"pool_id": "main"},
    )
    assert event.value == 100.0
    assert event.unit == "percent"
    assert event.dimensions["pool_id"] == "main"

def test_deployment_event_valid():
    event = DeploymentEvent(
        service="payment-service",
        version="v2.8.1",
        previous_version="v2.8.0",
        git_commit="a91c42f",
        author="alice",
        status="completed",
    )
    assert event.version == "v2.8.1"
    assert event.previous_version == "v2.8.0"
    assert event.git_commit == "a91c42f"

def test_alert_event_valid():
    event = AlertEvent(
        alert_id="ALT-901",
        title="Payment Error Rate Spiking",
        service="payment-service",
        severity="critical",
        description="Error rate exceeded 5% over 5-minute sliding window",
    )
    assert event.alert_id == "ALT-901"
    assert event.active is True
    assert event.severity == "critical"

def test_incident_event_lifecycle():
    event = IncidentEvent(
        incident_id="INC-1042",
        title="Payment Service Database Connection Pool Exhaustion",
        service="payment-service",
        severity=IncidentSeverity.SEV1,
        status=IncidentStatus.DETECTED,
        summary="Service producing 480 DB timeouts/min after deployment v2.8.1",
        primary_root_cause=None,
        confidence_score=None,
    )
    assert event.severity == IncidentSeverity.SEV1
    assert event.status == IncidentStatus.DETECTED

    # Update state
    event.status = IncidentStatus.INVESTIGATING
    event.primary_root_cause = "Connection pool leak introduced in v2.8.1"
    event.confidence_score = 0.92
    assert event.confidence_score == 0.92
    assert event.status == IncidentStatus.INVESTIGATING

def test_ai_action_event_risk_levels():
    event = AIActionEvent(
        action_id="ACT-5501",
        incident_id="INC-1042",
        service="payment-service",
        risk_level=RiskLevel.HIGH,
        action_type="rollback",
        parameters={"from_version": "v2.8.1", "to_version": "v2.8.0"},
        status=ActionStatus.PROPOSED,
        rationale="Deployment v2.8.1 correlates directly with connection exhaustion.",
    )
    assert event.risk_level == RiskLevel.HIGH
    assert event.status == ActionStatus.PROPOSED
    assert event.parameters["to_version"] == "v2.8.0"
