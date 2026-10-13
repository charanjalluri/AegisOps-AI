"""
Tests for apps.mcp_logs.models
Verifies input validation limits, required fields, and serialization contracts offline.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from apps.mcp_logs.models import (
    GetCorrelatedErrorsInput,
    GetErrorRateInput,
    GetLogsAroundEventInput,
    GetServiceLogsInput,
    LogRecord,
    SearchLogsInput,
)


def test_search_logs_input_validation():
    valid = SearchLogsInput(
        service="payment-service",
        level="ERROR",
        pattern="timeout",
        limit=50,
    )
    assert valid.service == "payment-service"
    assert valid.limit == 50

    # Max limit clamped at 200
    with pytest.raises(ValidationError):
        SearchLogsInput(limit=500)

    # Min limit clamped at 1
    with pytest.raises(ValidationError):
        SearchLogsInput(limit=0)


def test_get_service_logs_input_validation():
    valid = GetServiceLogsInput(service="payment-service", limit=25)
    assert valid.service == "payment-service"
    assert valid.limit == 25
    assert valid.min_level == "INFO"

    with pytest.raises(ValidationError):
        GetServiceLogsInput()  # service is required


def test_get_error_rate_input_validation():
    valid = GetErrorRateInput(service="payment-service", interval_seconds=60, window_minutes=15)
    assert valid.interval_seconds == 60
    assert valid.window_minutes == 15

    with pytest.raises(ValidationError):
        GetErrorRateInput(service="payment-service", interval_seconds=2)  # ge=10


def test_get_correlated_errors_input_validation():
    valid = GetCorrelatedErrorsInput(service="payment-service", error_pattern="PoolTimeout")
    assert valid.service == "payment-service"
    assert valid.error_pattern == "PoolTimeout"
    assert valid.window_seconds == 60

    with pytest.raises(ValidationError):
        GetCorrelatedErrorsInput(service="payment-service")  # missing error_pattern


def test_get_logs_around_event_input_validation():
    now = datetime.now(timezone.utc)
    valid = GetLogsAroundEventInput(timestamp=now, window_seconds=45, service="payment-service")
    assert valid.timestamp == now
    assert valid.window_seconds == 45
    assert valid.service == "payment-service"
