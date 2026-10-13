"""
AegisOps AI - Sliding-Window Deterministic Anomaly Detector
Tracks real-time telemetry windows per service, evaluates deterministic rules,
enforces cooldown deduplication to prevent alert storms, and triggers automated incidents.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from apps.common.schemas.events import (
    DeploymentEvent,
    IncidentEvent,
    RawLogEvent,
    RawMetricEvent,
)
from apps.detection.incident_creator import IncidentCreator
from apps.detection.rules import (
    AnomalySignal,
    DBConnectionTimeoutRule,
    ErrorSpikeRule,
    LatencyAnomalyRule,
    ServiceTelemetryWindow,
)

logger = logging.getLogger("aegisops.detection.detector")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnomalyDetector:
    """
    Evaluates streaming telemetry over sliding windows and triggers deduplicated incidents.
    """

    def __init__(
        self,
        incident_creator: Optional[IncidentCreator] = None,
        window_seconds: float = 60.0,
        cooldown_seconds: float = 600.0,  # 10 minute cooldown per (service, rule)
        rules: Optional[List[Any]] = None,
    ):
        self.incident_creator = incident_creator or IncidentCreator()
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.rules = rules or [
            ErrorSpikeRule(),
            LatencyAnomalyRule(),
            DBConnectionTimeoutRule(),
        ]
        self.windows: Dict[str, ServiceTelemetryWindow] = {}
        # Cooldown state: (service, rule_name) -> {"incident_id": str, "triggered_at": datetime, "count": int}
        self.active_cooldowns: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def get_window(self, service: str) -> ServiceTelemetryWindow:
        if service not in self.windows:
            self.windows[service] = ServiceTelemetryWindow(service=service, window_seconds=self.window_seconds)
        return self.windows[service]

    def _is_in_cooldown(self, service: str, rule_name: str, now: datetime) -> Tuple[bool, Optional[str]]:
        key = (service, rule_name)
        if key in self.active_cooldowns:
            info = self.active_cooldowns[key]
            elapsed = (now - info["triggered_at"]).total_seconds()
            if elapsed < self.cooldown_seconds:
                info["count"] += 1
                info["last_seen"] = now
                return True, info["incident_id"]
            else:
                # Cooldown expired
                del self.active_cooldowns[key]
        return False, None

    async def ingest_event(self, event: Union[RawLogEvent, RawMetricEvent, DeploymentEvent]) -> Optional[IncidentEvent]:
        """Ingests a single telemetry event, updates sliding window, and evaluates rules."""
        service = getattr(event, "service", None)
        if not service:
            return None

        window = self.get_window(service)
        now = utc_now()

        if isinstance(event, RawLogEvent):
            window.logs.append(event)
        elif isinstance(event, RawMetricEvent):
            window.metrics.append(event)

        # Prune old window events
        cutoff = now - timedelta(seconds=self.window_seconds)
        window.prune(cutoff)

        # Evaluate rules
        return await self.evaluate_window(window, now)

    async def evaluate_window(self, window: ServiceTelemetryWindow, now: Optional[datetime] = None) -> Optional[IncidentEvent]:
        eval_time = now or utc_now()

        for rule in self.rules:
            signal: Optional[AnomalySignal] = rule.evaluate(window)
            if signal:
                in_cooldown, existing_id = self._is_in_cooldown(signal.service, signal.rule_name, eval_time)
                if in_cooldown:
                    logger.info(
                        f"Suppressed duplicate incident for {signal.service} ({signal.rule_name}) "
                        f"under cooldown for existing incident {existing_id}"
                    )
                    continue

                # Create new incident
                incident_event = await self.incident_creator.create_incident(signal)

                # Set cooldown
                self.active_cooldowns[(signal.service, signal.rule_name)] = {
                    "incident_id": incident_event.incident_id,
                    "triggered_at": eval_time,
                    "last_seen": eval_time,
                    "count": 1,
                }
                return incident_event

        return None

    def reset_cooldown(self, service: Optional[str] = None, rule_name: Optional[str] = None):
        if not service and not rule_name:
            self.active_cooldowns.clear()
        else:
            to_remove = [
                k for k in self.active_cooldowns
                if (not service or k[0] == service) and (not rule_name or k[1] == rule_name)
            ]
            for k in to_remove:
                del self.active_cooldowns[k]
