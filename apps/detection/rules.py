"""
AegisOps AI - Deterministic Anomaly Detection Rules & Signal Models
Defines rule evaluations for error spikes, latency anomalies, and database pool timeouts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from apps.common.schemas.events import IncidentSeverity, LogLevel, RawLogEvent, RawMetricEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AnomalySignal:
    rule_name: str
    service: str
    severity: IncidentSeverity
    title: str
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class ServiceTelemetryWindow:
    """Sliding-window telemetry sample accumulator for a single service."""
    service: str
    window_seconds: float = 60.0
    logs: List[RawLogEvent] = field(default_factory=list)
    metrics: List[RawMetricEvent] = field(default_factory=list)

    def prune(self, cutoff_time: datetime):
        self.logs = [log for log in self.logs if log.timestamp >= cutoff_time]
        self.metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]

    @property
    def total_requests(self) -> int:
        req_metrics = [m for m in self.metrics if "request" in m.metric_name.lower()]
        return len(req_metrics) if req_metrics else len(self.logs)

    @property
    def error_logs(self) -> List[RawLogEvent]:
        return [l for l in self.logs if l.level in (LogLevel.ERROR, LogLevel.CRITICAL)]

    @property
    def error_metrics(self) -> List[RawMetricEvent]:
        return [
            m for m in self.metrics
            if m.dimensions.get("status", "").startswith("5") or "error" in m.metric_name.lower()
        ]

    @property
    def latencies(self) -> List[float]:
        return [
            m.value for m in self.metrics
            if "duration" in m.metric_name.lower() or "latency" in m.metric_name.lower()
        ]


class ErrorSpikeRule:
    """Detects when error rate exceeds threshold (e.g. > 5%) or absolute error count spike in the window."""

    def __init__(self, error_rate_threshold_pct: float = 5.0, min_errors: int = 5):
        self.name = "ErrorSpikeRule"
        self.error_rate_threshold_pct = error_rate_threshold_pct
        self.min_errors = min_errors

    def evaluate(self, window: ServiceTelemetryWindow) -> Optional[AnomalySignal]:
        err_count = len(window.error_logs) + len(window.error_metrics)
        total = max(window.total_requests, err_count, 1)
        err_pct = (err_count / total) * 100.0

        if err_count >= self.min_errors and err_pct >= self.error_rate_threshold_pct:
            return AnomalySignal(
                rule_name=self.name,
                service=window.service,
                severity=IncidentSeverity.SEV2,
                title=f"Error rate spike in {window.service} ({err_pct:.1f}%)",
                summary=(
                    f"{window.service} error rate reached {err_pct:.1f}% "
                    f"({err_count} errors across {total} events) in 60s sliding window."
                ),
                metrics={
                    "error_count": err_count,
                    "total_events": total,
                    "error_rate_pct": round(err_pct, 2),
                    "threshold_pct": self.error_rate_threshold_pct,
                },
            )
        return None


class LatencyAnomalyRule:
    """Detects latency anomalies when average or p95 latency exceeds threshold."""

    def __init__(self, p95_threshold_ms: float = 1000.0, avg_threshold_ms: float = 800.0, min_samples: int = 5):
        self.name = "LatencyAnomalyRule"
        self.p95_threshold_ms = p95_threshold_ms
        self.avg_threshold_ms = avg_threshold_ms
        self.min_samples = min_samples

    def evaluate(self, window: ServiceTelemetryWindow) -> Optional[AnomalySignal]:
        latencies = sorted(window.latencies)
        if len(latencies) < self.min_samples:
            return None

        avg_lat = sum(latencies) / len(latencies)
        p95_idx = int(len(latencies) * 0.95)
        p95_lat = latencies[min(p95_idx, len(latencies) - 1)]

        if p95_lat >= self.p95_threshold_ms or avg_lat >= self.avg_threshold_ms:
            return AnomalySignal(
                rule_name=self.name,
                service=window.service,
                severity=IncidentSeverity.SEV2,
                title=f"High latency anomaly in {window.service} (p95: {p95_lat:.0f}ms)",
                summary=(
                    f"{window.service} latency exceeded performance threshold: "
                    f"p95={p95_lat:.1f}ms (threshold {self.p95_threshold_ms}ms), "
                    f"avg={avg_lat:.1f}ms."
                ),
                metrics={
                    "p95_latency_ms": round(p95_lat, 2),
                    "avg_latency_ms": round(avg_lat, 2),
                    "sample_count": len(latencies),
                    "threshold_ms": self.p95_threshold_ms,
                },
            )
        return None


class DBConnectionTimeoutRule:
    """Detects database connection pool timeouts and exhaustion in logs or metrics."""

    TIMEOUT_KEYWORDS = (
        "pooltimeout",
        "connection pool exhausted",
        "timeout acquiring connection",
        "connection pool is full",
        "could not obtain a database connection",
        "connection limit exceeded",
    )

    def __init__(self):
        self.name = "DBConnectionTimeoutRule"

    def evaluate(self, window: ServiceTelemetryWindow) -> Optional[AnomalySignal]:
        matching_logs = []
        for log in window.logs:
            lower_msg = log.message.lower()
            if any(kw in lower_msg for kw in self.TIMEOUT_KEYWORDS):
                matching_logs.append(log)

        exhaustion_metrics = [
            m for m in window.metrics
            if "pool.exhausted" in m.metric_name.lower() and m.value > 0
        ]

        if matching_logs or exhaustion_metrics:
            sample_msg = matching_logs[0].message if matching_logs else "Connection pool exhausted metric triggered"
            return AnomalySignal(
                rule_name=self.name,
                service=window.service,
                severity=IncidentSeverity.SEV1,
                title=f"Database connection pool exhaustion in {window.service}",
                summary=(
                    f"{window.service} detected database connection pool exhaustion: "
                    f"'{sample_msg[:120]}'. {len(matching_logs)} timeout log events observed."
                ),
                metrics={
                    "matching_logs_count": len(matching_logs),
                    "exhaustion_metric_count": len(exhaustion_metrics),
                    "sample_error": sample_msg[:200],
                },
            )
        return None
