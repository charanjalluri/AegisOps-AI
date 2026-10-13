"""
AegisOps AI - Telemetry Ingestion Consumer Service
Consumes operational telemetry from Kafka topics and micro-batches into PostgreSQL.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union
import asyncpg
from aiokafka import AIOKafkaConsumer

from apps.common.schemas.events import (
    DeploymentEvent,
    RawLogEvent,
    RawMetricEvent,
)
from apps.ingestion.database import (
    batch_insert_deployments,
    batch_insert_logs,
    batch_insert_metrics,
)
from apps.ingestion.models import (
    deployment_event_to_row,
    log_event_to_row,
    metric_event_to_row,
)

logger = logging.getLogger("aegisops.ingestion.consumer")


class TelemetryConsumer:
    """
    High-throughput asynchronous Kafka consumer with micro-batching persistence into PostgreSQL
    and real-time event dispatching to anomaly detection listeners.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topics: Optional[List[str]] = None,
        batch_size: int = 100,
        flush_interval_seconds: float = 1.0,
        pool: Optional[asyncpg.Pool] = None,
        event_listener: Optional[Callable[[Union[RawLogEvent, RawMetricEvent, DeploymentEvent]], Coroutine[Any, Any, None]]] = None,
    ):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
        self.topics = topics or ["logs.raw", "metrics.raw", "deployments.events"]
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.pool = pool
        self.event_listener = event_listener

        # Internal micro-batch buffers
        self.log_buffer: List[Tuple] = []
        self.metric_buffer: List[Tuple] = []
        self.deployment_buffer: List[Tuple] = []

        self.last_flush_time = time.time()
        self.running = False
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._flush_lock = asyncio.Lock()

    @property
    def total_buffered(self) -> int:
        return len(self.log_buffer) + len(self.metric_buffer) + len(self.deployment_buffer)

    async def process_raw_message(self, topic: str, raw_payload: Union[str, bytes, dict]) -> Optional[Any]:
        """Parses raw Kafka payload, enqueues to buffer, and notifies listener."""
        try:
            if isinstance(raw_payload, (str, bytes)):
                data = json.loads(raw_payload)
            else:
                data = raw_payload

            event: Optional[Union[RawLogEvent, RawMetricEvent, DeploymentEvent]] = None

            if topic == "logs.raw":
                event = RawLogEvent(**data)
                self.log_buffer.append(log_event_to_row(event))
            elif topic == "metrics.raw":
                event = RawMetricEvent(**data)
                self.metric_buffer.append(metric_event_to_row(event))
            elif topic == "deployments.events":
                event = DeploymentEvent(**data)
                self.deployment_buffer.append(deployment_event_to_row(event))
            else:
                logger.warning(f"Unhandled topic: {topic}")
                return None

            # Notify event listener (e.g. AnomalyDetector)
            if self.event_listener and event:
                try:
                    await self.event_listener(event)
                except Exception as ex:
                    logger.error(f"Error in event listener callback: {ex}")

            # Check if buffer size threshold reached
            if self.total_buffered >= self.batch_size:
                await self.flush()

            return event

        except Exception as e:
            logger.error(f"Malformed telemetry message on topic {topic}: {e}")
            return None

    async def flush(self) -> Dict[str, int]:
        """Flushes buffered records to PostgreSQL."""
        async with self._flush_lock:
            logs_to_insert = self.log_buffer[:]
            metrics_to_insert = self.metric_buffer[:]
            deployments_to_insert = self.deployment_buffer[:]

            self.log_buffer.clear()
            self.metric_buffer.clear()
            self.deployment_buffer.clear()
            self.last_flush_time = time.time()

            counts = {
                "logs": len(logs_to_insert),
                "metrics": len(metrics_to_insert),
                "deployments": len(deployments_to_insert),
            }

            if not self.pool:
                # If running without database pool (e.g. dry-run or unit test), return counts
                return counts

            try:
                if logs_to_insert:
                    await batch_insert_logs(self.pool, logs_to_insert)
                if metrics_to_insert:
                    await batch_insert_metrics(self.pool, metrics_to_insert)
                if deployments_to_insert:
                    await batch_insert_deployments(self.pool, deployments_to_insert)
            except Exception as e:
                logger.error(f"Failed to batch insert telemetry into database: {e}")
                # In production, messages would route to dead-letter queue or retry

            return counts

    async def start(self):
        """Starts Kafka consumer loop."""
        self.running = True
        self.consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id="aegisops-telemetry-ingestion",
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self.consumer.start()
        logger.info(f"TelemetryConsumer connected to {self.bootstrap_servers} on topics {self.topics}")

        try:
            while self.running:
                # Poll with timeout to support interval flushing
                try:
                    msg_batch = await self.consumer.getmany(timeout_ms=500, max_records=self.batch_size)
                    for tp, messages in msg_batch.items():
                        for msg in messages:
                            await self.process_raw_message(msg.topic, msg.value)

                    # Interval-based flush
                    if self.total_buffered > 0 and (time.time() - self.last_flush_time) >= self.flush_interval_seconds:
                        await self.flush()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error during Kafka polling: {e}")
                    await asyncio.sleep(1.0)
        finally:
            await self.stop()

    async def stop(self):
        """Gracefully flushes remaining buffers and closes consumer."""
        self.running = False
        if self.total_buffered > 0:
            await self.flush()
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None
        logger.info("TelemetryConsumer stopped.")
