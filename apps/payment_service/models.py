"""
Payment Service Request and Response Models
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class PaymentRequest(BaseModel):
    account_id: str
    amount: float = Field(gt=0, description="Payment amount must be greater than zero")
    currency: str = "USD"
    description: Optional[str] = "Standard payment transaction"

class PaymentResponse(BaseModel):
    payment_id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    amount: float
    currency: str
    status: str = "completed"
    latency_ms: float
    created_at: datetime = Field(default_factory=utc_now)

class PaymentHealth(BaseModel):
    service: str = "payment-service"
    version: str = "v2.8.0"
    status: str = "healthy"
    db_connected: bool = True
    active_pool_connections: int = 5
    max_pool_connections: int = 50
    pool_utilization_pct: float = 10.0

class PaymentMetrics(BaseModel):
    service: str = "payment-service"
    total_transactions: int = 0
    successful_transactions: int = 0
    failed_transactions: int = 0
    error_rate_pct: float = 0.0
    avg_latency_ms: float = 145.0
