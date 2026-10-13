"""
AegisOps AI - Telemetry Ingestion Package
"""

from apps.ingestion.consumer import TelemetryConsumer
from apps.ingestion.database import (
    batch_insert_deployments,
    batch_insert_logs,
    batch_insert_metrics,
    get_connection_pool,
    init_db_schema,
    insert_incident,
)
from apps.ingestion.models import (
    deployment_event_to_row,
    incident_event_to_row,
    log_event_to_row,
    metric_event_to_row,
)

__all__ = [
    "TelemetryConsumer",
    "get_connection_pool",
    "init_db_schema",
    "batch_insert_logs",
    "batch_insert_metrics",
    "batch_insert_deployments",
    "insert_incident",
    "log_event_to_row",
    "metric_event_to_row",
    "deployment_event_to_row",
    "incident_event_to_row",
]
