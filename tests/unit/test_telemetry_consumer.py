"""
Tests for apps.ingestion.consumer
Verifies TelemetryConsumer message processing, buffering, batch thresholds,
listener callbacks, and error handling offline without requiring live Kafka or Postgres.
"""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest

from apps.common.schemas.events import LogLevel, RawLogEvent
from apps.ingestion.consumer import TelemetryConsumer


@pytest.mark.anyio
async def test_consumer_buffers_and_flushes_on_batch_size():
    consumer = TelemetryConsumer(batch_size=3)

    log_payload = {
        "service": "payment-service",
        "level": "INFO",
        "message": "Processed payment",
    }

    # Message 1
    ev1 = await consumer.process_raw_message("logs.raw", json.dumps(log_payload))
    assert ev1 is not None
    assert consumer.total_buffered == 1

    # Message 2
    ev2 = await consumer.process_raw_message("logs.raw", json.dumps(log_payload))
    assert ev2 is not None
    assert consumer.total_buffered == 2

    # Message 3: triggers flush automatically
    ev3 = await consumer.process_raw_message("logs.raw", json.dumps(log_payload))
    assert ev3 is not None
    assert consumer.total_buffered == 0  # Flushed!


@pytest.mark.anyio
async def test_consumer_notifies_event_listener():
    received_events = []

    async def listener(event):
        received_events.append(event)

    consumer = TelemetryConsumer(batch_size=10, event_listener=listener)

    metric_payload = {
        "service": "payment-service",
        "metric_name": "http.request.duration_ms",
        "value": 150.0,
    }
    await consumer.process_raw_message("metrics.raw", metric_payload)

    assert len(received_events) == 1
    assert received_events[0].metric_name == "http.request.duration_ms"
    assert received_events[0].value == 150.0


@pytest.mark.anyio
async def test_consumer_handles_malformed_messages_gracefully():
    consumer = TelemetryConsumer()

    # Broken JSON
    res1 = await consumer.process_raw_message("logs.raw", "not-a-json-string{")
    assert res1 is None
    assert consumer.total_buffered == 0

    # Missing required field 'service'
    res2 = await consumer.process_raw_message("logs.raw", json.dumps({"message": "no service"}))
    assert res2 is None
    assert consumer.total_buffered == 0


@pytest.mark.anyio
async def test_consumer_manual_flush_with_mock_pool():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire.return_value = mock_ctx

    consumer = TelemetryConsumer(pool=mock_pool, batch_size=100)

    await consumer.process_raw_message(
        "deployments.events",
        {
            "service": "payment-service",
            "version": "v2.8.1",
            "git_commit": "abc1234",
        },
    )
    assert consumer.total_buffered == 1

    counts = await consumer.flush()
    assert counts["deployments"] == 1
    assert counts["logs"] == 0
    assert consumer.total_buffered == 0
    assert mock_conn.executemany.called
