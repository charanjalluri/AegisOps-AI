"""
AegisOps AI - Observability REST Router (UI-05)
Performs active TCP/HTTP socket health probes across infrastructure and managed MCP servers,
categorizing each service into one of 4 explicit states: healthy, unhealthy, unknown, or stale.
Credentials and passwords are strictly redacted from output schemas.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
import os
import socket
import time
from typing import Any, Callable, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/observability", tags=["observability"])


class ServiceHealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STALE = "stale"


class ServiceHealthItem(BaseModel):
    service: str
    port: int
    status: ServiceHealthStatus
    latency_ms: float = Field(ge=0.0)
    last_probe_timestamp: str
    details: Optional[str] = None


class ObservabilityStatus(BaseModel):
    overall_status: str  # "healthy", "degraded", "outage"
    healthy_count: int
    total_count: int
    probed_at: str
    services: List[ServiceHealthItem]


DEFAULT_PROBE_TARGETS = [
    {"service": "postgresql", "host": "localhost", "port": 5432, "env_host": "POSTGRES_HOST", "env_port": "POSTGRES_PORT"},
    {"service": "kafka", "host": "localhost", "port": 29092, "env_host": "KAFKA_HOST", "env_port": "KAFKA_PORT"},
    {"service": "qdrant", "host": "localhost", "port": 6333, "env_host": "QDRANT_HOST", "env_port": "QDRANT_PORT"},
    {"service": "n8n", "host": "localhost", "port": 5678, "env_host": "N8N_HOST", "env_port": "N8N_PORT"},
    {"service": "payment-service", "host": "localhost", "port": 8001, "env_host": "PAYMENT_SERVICE_HOST", "env_port": "PAYMENT_SERVICE_PORT"},
    {"service": "mcp_logs", "host": "localhost", "port": 8002, "env_host": "MCP_LOGS_HOST", "env_port": "MCP_LOGS_PORT"},
    {"service": "mcp_database", "host": "localhost", "port": 8003, "env_host": "MCP_DATABASE_HOST", "env_port": "MCP_DATABASE_PORT"},
    {"service": "mcp_github", "host": "localhost", "port": 8004, "env_host": "MCP_GITHUB_HOST", "env_port": "MCP_GITHUB_PORT"},
    {"service": "mcp_incident", "host": "localhost", "port": 8005, "env_host": "MCP_INCIDENT_HOST", "env_port": "MCP_INCIDENT_PORT"},
    {"service": "mcp_deployment", "host": "localhost", "port": 8006, "env_host": "MCP_DEPLOYMENT_HOST", "env_port": "MCP_DEPLOYMENT_PORT"},
    {"service": "mcp_n8n", "host": "localhost", "port": 8007, "env_host": "MCP_N8N_HOST", "env_port": "MCP_N8N_PORT"},
]

# Heartbeat registry to detect stale services (service -> last_seen_iso)
_service_heartbeats: Dict[str, str] = {}
_custom_probe_override: Optional[Callable[[str, str, int, float], ServiceHealthItem]] = None


def set_custom_probe_override(fn: Optional[Callable[[str, str, int, float], ServiceHealthItem]]) -> None:
    """Sets a custom probe function for offline unit test simulation."""
    global _custom_probe_override
    _custom_probe_override = fn


def record_heartbeat(service: str, timestamp_iso: Optional[str] = None) -> None:
    """Records a telemetry heartbeat for a service."""
    _service_heartbeats[service] = timestamp_iso or datetime.now(timezone.utc).isoformat()


def clear_heartbeats() -> None:
    _service_heartbeats.clear()


async def probe_service(
    service: str,
    host: str,
    port: int,
    timeout: float = 1.5,
    stale_threshold_seconds: float = 60.0,
) -> ServiceHealthItem:
    """
    Executes a real TCP probe against the target host and port.
    Returns ServiceHealthItem with status: healthy, unhealthy, unknown, or stale.
    """
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    if _custom_probe_override:
        return _custom_probe_override(service, host, port, timeout)

    # Check stale condition if heartbeat exists but is older than threshold
    last_hb = _service_heartbeats.get(service)
    if last_hb:
        try:
            hb_dt = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
            age_sec = (now_dt - hb_dt).total_seconds()
            if age_sec > stale_threshold_seconds:
                return ServiceHealthItem(
                    service=service,
                    port=port,
                    status=ServiceHealthStatus.STALE,
                    latency_ms=0.0,
                    last_probe_timestamp=now_iso,
                    details=f"Last telemetry received {int(age_sec)}s ago (> {int(stale_threshold_seconds)}s threshold).",
                )
        except Exception:
            pass

    start = time.perf_counter()
    loop = asyncio.get_running_loop()

    def _sync_tcp_probe():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            sock.close()
            return result
        except socket.timeout:
            sock.close()
            return -1  # timeout
        except Exception as exc:
            sock.close()
            return exc

    try:
        res = await asyncio.wait_for(loop.run_in_executor(None, _sync_tcp_probe), timeout=timeout + 0.5)
        latency = round((time.perf_counter() - start) * 1000.0, 2)

        if res == 0:
            # Successfully connected
            record_heartbeat(service, now_iso)
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=latency,
                last_probe_timestamp=now_iso,
                details=f"TCP port {port} responsive.",
            )
        elif res == -1:
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.UNKNOWN,
                latency_ms=latency,
                last_probe_timestamp=now_iso,
                details=f"Probe timed out after {timeout}s.",
            )
        elif isinstance(res, int):
            # Non-zero error code (e.g. 10061 connection refused)
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.UNHEALTHY,
                latency_ms=latency,
                last_probe_timestamp=now_iso,
                details=f"Connection refused on port {port} (code {res}).",
            )
        else:
            return ServiceHealthItem(
                service=service,
                port=port,
                status=ServiceHealthStatus.UNKNOWN,
                latency_ms=latency,
                last_probe_timestamp=now_iso,
                details=f"Network resolution error: {str(res)}",
            )
    except asyncio.TimeoutError:
        latency = round((time.perf_counter() - start) * 1000.0, 2)
        return ServiceHealthItem(
            service=service,
            port=port,
            status=ServiceHealthStatus.UNKNOWN,
            latency_ms=latency,
            last_probe_timestamp=now_iso,
            details=f"Probe timed out after {timeout}s.",
        )


@router.get("/status", response_model=ObservabilityStatus)
async def get_observability_status() -> ObservabilityStatus:
    """
    Probes all monitored infrastructure and MCP endpoints concurrently.
    Categorizes status into healthy, unhealthy, unknown, or stale.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    tasks = []
    for target in DEFAULT_PROBE_TARGETS:
        service = target["service"]
        host = os.getenv(target["env_host"], target["host"])
        port = int(os.getenv(target["env_port"], str(target["port"])))
        tasks.append(probe_service(service, host, port))

    results: List[ServiceHealthItem] = await asyncio.gather(*tasks)

    healthy_count = sum(1 for s in results if s.status == ServiceHealthStatus.HEALTHY)
    unhealthy_count = sum(1 for s in results if s.status == ServiceHealthStatus.UNHEALTHY)
    total_count = len(results)

    if healthy_count == total_count:
        overall = "healthy"
    elif unhealthy_count > 0:
        overall = "degraded" if healthy_count > 0 else "outage"
    else:
        overall = "degraded"

    return ObservabilityStatus(
        overall_status=overall,
        healthy_count=healthy_count,
        total_count=total_count,
        probed_at=now_iso,
        services=results,
    )
