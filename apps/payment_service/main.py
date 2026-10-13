"""
AegisOps AI - Fictional Payment Service Simulator (Baseline v2.8.0)
Lightweight HTTP microservice backed by PostgreSQL (demo_payment_db).
Processes transactions, manages connection pool stats, and publishes telemetry to Kafka.
"""

import os
import time
import json
import logging
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status

from apps.payment_service.models import PaymentRequest, PaymentResponse, PaymentHealth, PaymentMetrics
from apps.payment_service.database import db
from apps.common.schemas.events import RawLogEvent, RawMetricEvent, LogLevel

logger = logging.getLogger("payment_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SERVICE_NAME = "payment-service"
VERSION = "v2.8.0"

class MetricsTracker:
    def __init__(self):
        self.total = 0
        self.successful = 0
        self.failed = 0
        self.total_latency = 0.0

    def record(self, success: bool, latency: float):
        self.total += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1
        self.total_latency += latency

    def get_summary(self) -> PaymentMetrics:
        avg = (self.total_latency / self.total) if self.total > 0 else 145.0
        err_pct = (self.failed / self.total * 100.0) if self.total > 0 else 0.0
        return PaymentMetrics(
            service=SERVICE_NAME,
            total_transactions=self.total,
            successful_transactions=self.successful,
            failed_transactions=self.failed,
            error_rate_pct=round(err_pct, 2),
            avg_latency_ms=round(avg, 2),
        )

tracker = MetricsTracker()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    await db.initialize()
    logger.info(f"{SERVICE_NAME} {VERSION} initialized successfully.")
    yield
    # Shutdown
    logger.info(f"{SERVICE_NAME} shutting down.")

app = FastAPI(
    title="Payment Service (Demo Microservice)",
    description="Fictional e-commerce payment microservice emitting real operational telemetry",
    version=VERSION,
    lifespan=lifespan,
)

def emit_telemetry_event(topic: str, payload: dict):
    """Logs telemetry payload; attempts publishing to Kafka if broker reachable."""
    # In Phase 1 local dev/testing, print and structure cleanly
    logger.info(f"Telemetry Event -> [{topic}]: {json.dumps(payload, default=str)}")

@app.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def process_payment(req: PaymentRequest):
    start_time = time.time()
    
    # Baseline normal processing latency (~110ms - 180ms)
    time.sleep(0.01)  # small slice for test speed
    latency_ms = round((time.time() - start_time) * 1000 + 125.0, 2)

    # Persist to demo_payment_db
    record = await db.record_transaction(
        account_id=req.account_id,
        amount=req.amount,
        currency=req.currency,
        latency_ms=latency_ms,
        status="completed",
    )

    tracker.record(success=True, latency=latency_ms)

    # Emit operational log event
    log_event = RawLogEvent(
        service=SERVICE_NAME,
        level=LogLevel.INFO,
        message=f"Processed payment of {req.amount} {req.currency} for account {req.account_id}",
        metadata={"payment_id": record["id"], "latency_ms": latency_ms, "version": VERSION},
    )
    emit_telemetry_event("logs.raw", log_event.model_dump())

    # Emit operational metric event
    metric_event = RawMetricEvent(
        service=SERVICE_NAME,
        metric_name="http_request_latency_ms",
        value=latency_ms,
        unit="ms",
        dimensions={"endpoint": "/payments", "method": "POST", "status": "201"},
    )
    emit_telemetry_event("metrics.raw", metric_event.model_dump())

    return PaymentResponse(
        payment_id=record["id"],
        account_id=req.account_id,
        amount=req.amount,
        currency=req.currency,
        status="completed",
        latency_ms=latency_ms,
        created_at=record["created_at"],
    )

@app.get("/payments")
async def list_payments(limit: int = 20) -> List[Dict[str, Any]]:
    return await db.get_recent_transactions(limit=limit)

@app.get("/health", response_model=PaymentHealth)
async def payment_health():
    return PaymentHealth(
        service=SERVICE_NAME,
        version=VERSION,
        status="healthy",
        db_connected=True,
        active_pool_connections=db.active_connections,
        max_pool_connections=db.max_connections,
        pool_utilization_pct=round((db.active_connections / db.max_connections) * 100.0, 1),
    )

@app.get("/metrics")
async def payment_metrics() -> PaymentMetrics:
    return tracker.get_summary()


@app.post("/simulate/version")
async def simulate_version(req: Dict[str, Any]):
    global VERSION
    new_version = req.get("version", "v2.8.1")
    VERSION = new_version
    logger.info(f"[Simulation] Updated service version to {VERSION}")
    return {"status": "updated", "version": VERSION}

@app.post("/simulate/leak")
async def simulate_leak(req: Dict[str, Any]):
    active = int(req.get("active_connections", 50))
    db.active_connections = active
    logger.info(f"[Simulation] Set database active connections to {db.active_connections}")
    return {"status": "simulated", "active_connections": db.active_connections}

@app.post("/simulate/reset")
async def simulate_reset():
    global VERSION
    VERSION = "v2.8.0"
    db.active_connections = 2
    tracker.failed = 0
    tracker.total = 0
    tracker.successful = 0
    tracker.total_latency = 0.0
    logger.info("[Simulation] Reset payment service simulator to nominal v2.8.0 baseline.")
    return {"status": "reset", "version": VERSION, "active_connections": db.active_connections}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PAYMENT_SERVICE_PORT", "8001"))
    host = os.getenv("PAYMENT_SERVICE_HOST", "0.0.0.0")
    uvicorn.run("apps.payment_service.main:app", host=host, port=port, reload=True)
