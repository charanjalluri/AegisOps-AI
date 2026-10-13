"""
Tests for apps.mcp_logs.tools
Verifies log search, service filtering, error rate analytics, cross-service correlation,
and event window extraction offline using in-memory mock datasets.
"""

from datetime import datetime, timedelta, timezone
import pytest

from apps.mcp_logs.models import (
    GetCorrelatedErrorsInput,
    GetErrorRateInput,
    GetLogsAroundEventInput,
    GetServiceLogsInput,
    SearchLogsInput,
)
from apps.mcp_logs.tools import LogsTools


@pytest.fixture
def sample_logs():
    base_time = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    logs = []
    # 20 normal logs for payment-service
    for i in range(20):
        logs.append({
            "id": f"log-norm-{i}",
            "timestamp": base_time + timedelta(seconds=i * 5),
            "service": "payment-service",
            "level": "INFO",
            "message": f"Processed transaction #{i}",
            "environment": "staging",
            "trace_id": f"tr-{i}",
            "metadata": {},
        })
    # 5 error logs with connection pool timeout
    for i in range(5):
        logs.append({
            "id": f"log-err-{i}",
            "timestamp": base_time + timedelta(seconds=60 + i * 2),
            "service": "payment-service",
            "level": "ERROR",
            "message": f"ConnectionPoolTimeout: connection pool exhausted (retry {i})",
            "environment": "staging",
            "trace_id": f"tr-err-{i}",
            "metadata": {},
        })
    # 5 logs for another service (auth-service)
    for i in range(5):
        logs.append({
            "id": f"log-auth-{i}",
            "timestamp": base_time + timedelta(seconds=i * 10),
            "service": "auth-service",
            "level": "INFO",
            "message": f"Auth token verified for user {i}",
            "environment": "staging",
            "trace_id": f"tr-auth-{i}",
            "metadata": {},
        })
    return logs


@pytest.mark.anyio
async def test_search_logs_filters(sample_logs):
    tools = LogsTools(in_memory_logs=sample_logs)

    # Filter by service
    res_service = await tools.search_logs(SearchLogsInput(service="auth-service"))
    assert res_service.count == 5
    assert all(l.service == "auth-service" for l in res_service.logs)

    # Filter by level
    res_level = await tools.search_logs(SearchLogsInput(level="ERROR"))
    assert res_level.count == 5
    assert all(l.level == "ERROR" for l in res_level.logs)

    # Filter by message pattern
    res_pattern = await tools.search_logs(SearchLogsInput(pattern="ConnectionPoolTimeout"))
    assert res_pattern.count == 5
    assert all("ConnectionPoolTimeout" in l.message for l in res_pattern.logs)


@pytest.mark.anyio
async def test_get_service_logs_min_level(sample_logs):
    tools = LogsTools(in_memory_logs=sample_logs)

    # min_level="ERROR" should only return ERROR and above
    res = await tools.get_service_logs(GetServiceLogsInput(service="payment-service", min_level="ERROR"))
    assert res.count == 5
    assert all(l.level in ("ERROR", "CRITICAL") for l in res.logs)


@pytest.mark.anyio
async def test_get_error_rate_calculation(sample_logs):
    tools = LogsTools(in_memory_logs=sample_logs)

    # Calculate error rate with lookback
    now = datetime(2026, 10, 10, 12, 5, 0, tzinfo=timezone.utc)
    res = await tools.get_error_rate(
        GetErrorRateInput(service="payment-service", interval_seconds=60, window_minutes=60, end_time=now)
    )
    assert res.service == "payment-service"
    assert res.total_logs == 25
    assert res.total_errors == 5
    assert res.overall_error_rate_pct == 20.0
    assert len(res.buckets) > 0


@pytest.mark.anyio
async def test_get_correlated_errors(sample_logs):
    tools = LogsTools(in_memory_logs=sample_logs)

    res = await tools.get_correlated_errors(
        GetCorrelatedErrorsInput(service="payment-service", error_pattern="ConnectionPoolTimeout", window_seconds=30)
    )
    assert res.matching_errors_count == 5
    assert len(res.correlated_events) == 5
    assert res.correlated_events[0]["surrounding_logs_count"] > 0


@pytest.mark.anyio
async def test_get_logs_around_event(sample_logs):
    tools = LogsTools(in_memory_logs=sample_logs)

    # Anchor at the first error (12:01:00)
    anchor_time = datetime(2026, 10, 10, 12, 1, 0, tzinfo=timezone.utc)
    res = await tools.get_logs_around_event(
        GetLogsAroundEventInput(timestamp=anchor_time, window_seconds=40, service="payment-service")
    )
    assert res.target_timestamp == anchor_time
    assert res.total_logs > 0
    assert all(l.timestamp <= anchor_time for l in res.logs_before)
    assert all(l.timestamp > anchor_time for l in res.logs_after)
