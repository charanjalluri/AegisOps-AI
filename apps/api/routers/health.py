"""
AegisOps AI - Health and Readiness Probes Router
Evaluates liveness (/health) and decoupled readiness (/ready).
Hard dependencies: PostgreSQL (aegisops_db), Kafka broker.
Soft dependencies: Qdrant, n8n (informational; do not fail readiness).
"""

import os
import socket
from typing import Dict, Any
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Response, status

router = APIRouter(tags=["health"])

def ping_tcp_host(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

async def check_postgres(db_url: str = None, timeout: float = 2.0) -> Dict[str, Any]:
    if not db_url:
        db_url = os.getenv("AEGISOPS_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aegisops_db")
    
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    db_name = parsed.path.lstrip("/") or "aegisops_db"
    
    # TCP port connectivity test
    is_up = ping_tcp_host(host, port, timeout)
    if is_up:
        return {
            "status": "healthy",
            "host": host,
            "port": port,
            "database": db_name,
            "required": True,
        }
    return {
        "status": "unreachable",
        "host": host,
        "port": port,
        "database": db_name,
        "required": True,
        "error": f"Cannot connect to PostgreSQL at {host}:{port}",
    }

async def check_kafka(bootstrap_servers: str = None, timeout: float = 2.0) -> Dict[str, Any]:
    if not bootstrap_servers:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    
    first_broker = bootstrap_servers.split(",")[0]
    parts = first_broker.split(":")
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 9092
    
    is_up = ping_tcp_host(host, port, timeout)
    if is_up:
        return {
            "status": "healthy",
            "bootstrap_servers": bootstrap_servers,
            "required": True,
        }
    return {
        "status": "unreachable",
        "bootstrap_servers": bootstrap_servers,
        "required": True,
        "error": f"Cannot connect to Kafka broker at {host}:{port}",
    }

async def check_qdrant(qdrant_url: str = None, timeout: float = 1.5) -> Dict[str, Any]:
    if not qdrant_url:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{qdrant_url}/collections")
            if resp.status_code == 200:
                return {"status": "available", "url": qdrant_url, "required": False}
    except Exception as e:
        return {"status": "unavailable", "url": qdrant_url, "required": False, "note": "Soft dependency in Phase 1"}
    
    return {"status": "unavailable", "url": qdrant_url, "required": False, "note": "Soft dependency in Phase 1"}

async def check_n8n(n8n_url: str = None, timeout: float = 1.5) -> Dict[str, Any]:
    if not n8n_url:
        n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{n8n_url}/healthz")
            if resp.status_code in (200, 401):  # 401 means n8n is up but requires auth
                return {"status": "available", "url": n8n_url, "required": False}
    except Exception as e:
        return {"status": "unavailable", "url": n8n_url, "required": False, "note": "Soft dependency in Phase 1"}
    
    return {"status": "unavailable", "url": n8n_url, "required": False, "note": "Soft dependency in Phase 1"}

@router.get("/health")
async def liveness_probe() -> Dict[str, Any]:
    """Instant liveness check confirming the process is alive."""
    return {
        "status": "healthy",
        "service": "aegisops-api",
        "phase": 1,
    }

@router.get("/ready")
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """
    Readiness probe validating operational dependencies.
    PostgreSQL and Kafka are hard requirements (returns 503 if unreachable).
    Qdrant and n8n are soft/informational dependencies (does not cause 503).
    """
    postgres_status = await check_postgres()
    kafka_status = await check_kafka()
    qdrant_status = await check_qdrant()
    n8n_status = await check_n8n()

    hard_dependencies_healthy = (
        postgres_status["status"] == "healthy" and kafka_status["status"] == "healthy"
    )

    dependencies = {
        "postgres": postgres_status,
        "kafka": kafka_status,
        "qdrant": qdrant_status,
        "n8n": n8n_status,
    }

    if hard_dependencies_healthy:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "ready",
            "service": "aegisops-api",
            "dependencies": dependencies,
        }
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "service": "aegisops-api",
            "dependencies": dependencies,
        }
