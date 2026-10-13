"""
AegisOps AI - Telemetry Ingestion Data Models & Record Mappers
Converts Pydantic event objects into optimized database row tuples for asyncpg batch insertion.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from apps.common.schemas.events import (
    DeploymentEvent,
    IncidentEvent,
    RawLogEvent,
    RawMetricEvent,
)


def log_event_to_row(event: RawLogEvent) -> Tuple:
    try:
        row_id = UUID(event.event_id)
    except Exception:
        row_id = uuid4()

    return (
        row_id,
        event.timestamp,
        event.service,
        event.level.value if hasattr(event.level, "value") else str(event.level),
        event.message,
        event.environment,
        event.trace_id,
        json.dumps(event.metadata),
    )


def metric_event_to_row(event: RawMetricEvent) -> Tuple:
    try:
        row_id = UUID(event.event_id)
    except Exception:
        row_id = uuid4()

    return (
        row_id,
        event.timestamp,
        event.service,
        event.metric_name,
        float(event.value),
        event.unit,
        json.dumps(event.dimensions),
    )


def deployment_event_to_row(event: DeploymentEvent) -> Tuple:
    try:
        row_id = UUID(event.event_id)
    except Exception:
        row_id = uuid4()

    return (
        row_id,
        event.timestamp,
        event.service,
        event.version,
        event.previous_version,
        event.git_commit,
        event.author,
        event.status,
        json.dumps(event.metadata),
    )


def incident_event_to_row(event: IncidentEvent) -> Tuple:
    return (
        event.incident_id,
        event.title,
        event.service,
        event.severity.value if hasattr(event.severity, "value") else str(event.severity),
        event.status.value if hasattr(event.status, "value") else str(event.status),
        event.created_at,
        event.updated_at,
        event.summary,
        event.primary_root_cause,
        event.confidence_score,
        json.dumps(event.metadata),
    )
