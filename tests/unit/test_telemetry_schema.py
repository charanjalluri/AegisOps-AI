"""
Tests for infrastructure.postgres.schema.sql and apps.ingestion.models
Verifies SQL table definitions, indexes, and event-to-row tuple transformations offline.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from apps.common.schemas.events import (
    DeploymentEvent,
    IncidentEvent,
    IncidentSeverity,
    IncidentStatus,
    LogLevel,
    RawLogEvent,
    RawMetricEvent,
)
from apps.ingestion.models import (
    deployment_event_to_row,
    incident_event_to_row,
    log_event_to_row,
    metric_event_to_row,
)


def test_schema_sql_file_exists_and_contains_core_tables():
    schema_path = Path(__file__).resolve().parent.parent.parent / "infrastructure" / "postgres" / "schema.sql"
    assert schema_path.exists(), "schema.sql must exist"

    sql = schema_path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS raw_logs" in sql
    assert "CREATE TABLE IF NOT EXISTS raw_metrics" in sql
    assert "CREATE TABLE IF NOT EXISTS deployment_events" in sql
    assert "CREATE TABLE IF NOT EXISTS incidents" in sql
    assert "CREATE TABLE IF NOT EXISTS incident_events" in sql

    # Verify performance indexes
    assert "idx_raw_logs_service_timestamp" in sql
    assert "idx_raw_metrics_service_metric_timestamp" in sql
    assert "idx_incidents_service_status" in sql


def test_log_event_to_row_mapping():
    now = datetime.now(timezone.utc)
    event = RawLogEvent(
        event_id="550e8400-e29b-41d4-a716-446655440000",
        timestamp=now,
        service="payment-service",
        level=LogLevel.ERROR,
        message="Database connection pool timeout",
        environment="staging",
        trace_id="trace-abc-123",
        metadata={"pool_size": 10, "active": 10},
    )
    row = log_event_to_row(event)

    assert str(row[0]) == "550e8400-e29b-41d4-a716-446655440000"
    assert row[1] == now
    assert row[2] == "payment-service"
    assert row[3] == "ERROR"
    assert row[4] == "Database connection pool timeout"
    assert row[5] == "staging"
    assert row[6] == "trace-abc-123"
    assert '"pool_size": 10' in row[7]


def test_metric_event_to_row_mapping():
    now = datetime.now(timezone.utc)
    event = RawMetricEvent(
        event_id="660e8400-e29b-41d4-a716-446655440000",
        timestamp=now,
        service="payment-service",
        metric_name="http.request.duration_ms",
        value=1250.5,
        unit="ms",
        dimensions={"route": "/payments", "status": "500"},
    )
    row = metric_event_to_row(event)

    assert str(row[0]) == "660e8400-e29b-41d4-a716-446655440000"
    assert row[1] == now
    assert row[2] == "payment-service"
    assert row[3] == "http.request.duration_ms"
    assert row[4] == 1250.5
    assert row[5] == "ms"
    assert '"route": "/payments"' in row[6]


def test_deployment_and_incident_mapping():
    now = datetime.now(timezone.utc)
    dep_event = DeploymentEvent(
        service="payment-service",
        version="v2.8.1",
        previous_version="v2.8.0",
        git_commit="git-c0ffee1",
        author="alice",
    )
    dep_row = deployment_event_to_row(dep_event)
    assert dep_row[2] == "payment-service"
    assert dep_row[3] == "v2.8.1"
    assert dep_row[5] == "git-c0ffee1"
    assert dep_row[6] == "alice"

    inc_event = IncidentEvent(
        incident_id="inc-2026-001",
        title="High error rate in payment-service",
        service="payment-service",
        severity=IncidentSeverity.SEV1,
        status=IncidentStatus.DETECTED,
        summary="5xx error rate exceeded 15% threshold",
        primary_root_cause=None,
    )
    inc_row = incident_event_to_row(inc_event)
    assert inc_row[0] == "inc-2026-001"
    assert inc_row[1] == "High error rate in payment-service"
    assert inc_row[2] == "payment-service"
    assert inc_row[3] == "SEV-1"
    assert inc_row[4] == "detected"
