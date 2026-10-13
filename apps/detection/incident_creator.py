"""
AegisOps AI - Automated Incident Creator
Generates structured IncidentEvents from anomaly signals, persists to PostgreSQL,
and publishes to Kafka incidents.created topic.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
import asyncpg
from aiokafka import AIOKafkaProducer

from apps.common.schemas.events import IncidentEvent, IncidentStatus
from apps.detection.rules import AnomalySignal
from apps.ingestion.database import insert_incident
from apps.ingestion.models import incident_event_to_row

logger = logging.getLogger("aegisops.detection.incident_creator")


class IncidentCreator:
    def __init__(
        self,
        pool: Optional[asyncpg.Pool] = None,
        producer: Optional[AIOKafkaProducer] = None,
    ):
        self.pool = pool
        self.producer = producer

    async def create_incident(self, signal: AnomalySignal) -> IncidentEvent:
        now = datetime.now(timezone.utc)
        incident_id = f"inc-{uuid4().hex[:8]}"

        event = IncidentEvent(
            incident_id=incident_id,
            title=signal.title,
            service=signal.service,
            severity=signal.severity,
            status=IncidentStatus.DETECTED,
            created_at=now,
            updated_at=now,
            summary=signal.summary,
            metadata={
                "trigger_rule": signal.rule_name,
                "trigger_metrics": signal.metrics,
                "detected_at": now.isoformat(),
            },
        )

        # 1. Persist to PostgreSQL if pool is available
        if self.pool:
            try:
                row = incident_event_to_row(event)
                await insert_incident(self.pool, row)
                logger.info(f"Persisted incident {incident_id} ({signal.severity.value}) to database")
            except Exception as e:
                logger.error(f"Failed to persist incident {incident_id} to database: {e}")

        # 2. Publish to Kafka topic 'incidents.created' if producer is available
        if self.producer:
            try:
                payload = event.model_dump_json().encode("utf-8")
                await self.producer.send_and_wait("incidents.created", payload)
                logger.info(f"Published incident {incident_id} to Kafka topic 'incidents.created'")
            except Exception as e:
                logger.error(f"Failed to publish incident {incident_id} to Kafka: {e}")

        return event
