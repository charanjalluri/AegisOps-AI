"""
Tests for apps.detection.rules, detector, and incident_creator
Verifies error spikes, latency percentiles, DB pool timeouts, cooldown deduplication,
and automated incident creation offline.
"""

from datetime import datetime, timezone
import pytest

from apps.common.schemas.events import (
    IncidentSeverity,
    IncidentStatus,
    LogLevel,
    RawLogEvent,
    RawMetricEvent,
)
from apps.detection.detector import AnomalyDetector
from apps.detection.incident_creator import IncidentCreator
from apps.detection.rules import (
    DBConnectionTimeoutRule,
    ErrorSpikeRule,
    LatencyAnomalyRule,
    ServiceTelemetryWindow,
)


def test_error_spike_rule_triggers_above_threshold():
    rule = ErrorSpikeRule(error_rate_threshold_pct=10.0, min_errors=3)
    window = ServiceTelemetryWindow(service="payment-service")

    # Add 20 normal logs and 5 error logs -> 5/25 = 20% > 10%
    now = datetime.now(timezone.utc)
    for _ in range(20):
        window.logs.append(RawLogEvent(service="payment-service", level=LogLevel.INFO, message="ok", timestamp=now))
    for _ in range(5):
        window.logs.append(RawLogEvent(service="payment-service", level=LogLevel.ERROR, message="500 internal error", timestamp=now))

    signal = rule.evaluate(window)
    assert signal is not None
    assert signal.rule_name == "ErrorSpikeRule"
    assert signal.severity == IncidentSeverity.SEV2
    assert "payment-service" in signal.title
    assert signal.metrics["error_count"] == 5
    assert signal.metrics["error_rate_pct"] == 20.0


def test_error_spike_rule_ignores_below_threshold():
    rule = ErrorSpikeRule(error_rate_threshold_pct=10.0, min_errors=5)
    window = ServiceTelemetryWindow(service="payment-service")

    now = datetime.now(timezone.utc)
    # Only 2 errors: does not meet min_errors of 5
    for _ in range(20):
        window.logs.append(RawLogEvent(service="payment-service", level=LogLevel.INFO, message="ok", timestamp=now))
    for _ in range(2):
        window.logs.append(RawLogEvent(service="payment-service", level=LogLevel.ERROR, message="err", timestamp=now))

    assert rule.evaluate(window) is None


def test_latency_anomaly_rule_triggers_on_high_p95():
    rule = LatencyAnomalyRule(p95_threshold_ms=1000.0, min_samples=5)
    window = ServiceTelemetryWindow(service="payment-service")

    now = datetime.now(timezone.utc)
    latencies = [120.0, 150.0, 180.0, 200.0, 1500.0, 1800.0]
    for lat in latencies:
        window.metrics.append(
            RawMetricEvent(
                service="payment-service",
                metric_name="http.request.duration_ms",
                value=lat,
                timestamp=now,
            )
        )

    signal = rule.evaluate(window)
    assert signal is not None
    assert signal.rule_name == "LatencyAnomalyRule"
    assert signal.metrics["p95_latency_ms"] >= 1000.0


def test_db_connection_timeout_rule_triggers_on_keyword():
    rule = DBConnectionTimeoutRule()
    window = ServiceTelemetryWindow(service="payment-service")

    now = datetime.now(timezone.utc)
    window.logs.append(
        RawLogEvent(
            service="payment-service",
            level=LogLevel.ERROR,
            message="sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 10 reached, connection pool exhausted",
            timestamp=now,
        )
    )

    signal = rule.evaluate(window)
    assert signal is not None
    assert signal.rule_name == "DBConnectionTimeoutRule"
    assert signal.severity == IncidentSeverity.SEV1
    assert "Database connection pool exhaustion" in signal.title


@pytest.mark.anyio
async def test_anomaly_detector_cooldown_deduplication():
    detector = AnomalyDetector(cooldown_seconds=60.0)
    now = datetime.now(timezone.utc)

    # Trigger DB connection timeout
    log_event = RawLogEvent(
        service="payment-service",
        level=LogLevel.ERROR,
        message="timeout acquiring connection from pool",
        timestamp=now,
    )

    # First event -> triggers incident
    inc1 = await detector.ingest_event(log_event)
    assert inc1 is not None
    assert inc1.service == "payment-service"
    assert inc1.severity == IncidentSeverity.SEV1
    assert inc1.status == IncidentStatus.DETECTED

    # Second event immediately after -> suppressed by cooldown!
    inc2 = await detector.ingest_event(log_event)
    assert inc2 is None, "Duplicate incident during cooldown must be suppressed"

    # Reset cooldown -> should trigger again
    detector.reset_cooldown()
    inc3 = await detector.ingest_event(log_event)
    assert inc3 is not None
    assert inc3.incident_id != inc1.incident_id
