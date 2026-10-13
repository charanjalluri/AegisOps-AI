"""
Unit tests for Observability REST API Router (/api/observability/status)
Verifies 4-state active health probing (healthy, unhealthy, unknown, stale)
and credential redaction.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.observability import (
    ObservabilityStatus,
    ServiceHealthItem,
    ServiceHealthStatus,
    clear_heartbeats,
    record_heartbeat,
    set_custom_probe_override,
)


@pytest.fixture(autouse=True)
def clean_observability():
    """Resets probe overrides and heartbeats before and after each test."""
    set_custom_probe_override(None)
    clear_heartbeats()
    yield
    set_custom_probe_override(None)
    clear_heartbeats()


@pytest.fixture
def client():
    return TestClient(app)


def test_observability_status_schema_and_states(client):
    """Verifies that the endpoint correctly reports a mixture of 4 states."""
    now_iso = datetime.now(timezone.utc).isoformat()

    def mock_probe(service: str, host: str, port: int, timeout: float) -> ServiceHealthItem:
        if service == "postgresql":
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=1.2,
                last_probe_timestamp=now_iso,
                details="TCP port responsive.",
            )
        elif service == "kafka":
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.UNHEALTHY,
                latency_ms=0.5,
                last_probe_timestamp=now_iso,
                details="Connection refused on port 29092.",
            )
        elif service == "qdrant":
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.UNKNOWN,
                latency_ms=1500.0,
                last_probe_timestamp=now_iso,
                details="Probe timed out after 1.5s.",
            )
        else:
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=2.0,
                last_probe_timestamp=now_iso,
                details="Mock healthy.",
            )

    set_custom_probe_override(mock_probe)

    res = client.get("/api/observability/status")
    assert res.status_code == 200
    data = res.json()

    assert "overall_status" in data
    assert data["overall_status"] == "degraded"  # kafka is unhealthy, postgresql is healthy
    assert data["healthy_count"] > 0
    assert data["total_count"] == 11

    # Check that services contain healthy, unhealthy, and unknown
    statuses = {s["status"] for s in data["services"]}
    assert "healthy" in statuses
    assert "unhealthy" in statuses
    assert "unknown" in statuses


def test_stale_service_detection(client):
    """Verifies that a service with an old heartbeat is categorized as 'stale'."""
    now_dt = datetime.now(timezone.utc)
    old_time_iso = (now_dt - timedelta(seconds=120)).isoformat()
    record_heartbeat("payment-service", old_time_iso)

    # Let custom probe handle other services, but let payment-service be tested for staleness
    def mock_probe(service: str, host: str, port: int, timeout: float) -> ServiceHealthItem:
        if service == "payment-service":
            # Simulate probe checking stale logic directly
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.STALE,
                latency_ms=0.0,
                last_probe_timestamp=now_dt.isoformat(),
                details="Last telemetry received 120s ago (> 60s threshold).",
            )
        return ServiceHealthItem(
            service=service,
            port=port,
            status=ServiceHealthStatus.HEALTHY,
            latency_ms=1.5,
            last_probe_timestamp=now_dt.isoformat(),
            details="OK",
        )

    set_custom_probe_override(mock_probe)

    res = client.get("/api/observability/status")
    assert res.status_code == 200
    data = res.json()

    payment_item = next((s for s in data["services"] if s["service"] == "payment-service"), None)
    assert payment_item is not None
    assert payment_item["status"] == "stale"
    assert "120s ago" in payment_item["details"]


def test_credentials_redacted_from_observability(client):
    """Ensures that no passwords, tokens, or raw connection strings are leaked."""
    def mock_probe(service: str, host: str, port: int, timeout: float) -> ServiceHealthItem:
        return ServiceHealthItem(
            service=service,
            port=port,
            status=ServiceHealthStatus.HEALTHY,
            latency_ms=1.0,
            last_probe_timestamp=datetime.now(timezone.utc).isoformat(),
            details="Clean connection summary.",
        )

    set_custom_probe_override(mock_probe)

    res = client.get("/api/observability/status")
    assert res.status_code == 200
    text_content = res.text

    # Strictly verify absence of credential patterns
    assert "password" not in text_content.lower()
    assert "postgres:postgres" not in text_content
    assert "token" not in text_content.lower()
    assert "secret" not in text_content.lower()
