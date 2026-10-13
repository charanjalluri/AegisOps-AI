"""
AegisOps AI - Database MCP Pydantic V2 Models
Structured schemas for database health, connection pool inspection, slow queries, and read-only querying.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatabaseHealthResult(BaseModel):
    database: str = "demo_payment_db"
    status: str = "healthy"  # healthy, degraded, exhausted
    version: str = "PostgreSQL 16.2"
    uptime_seconds: float = 86400.0
    database_size_bytes: int = 24576000
    total_connections: int = 10
    max_connections: int = 50


class ConnectionPoolResult(BaseModel):
    database: str = "demo_payment_db"
    total_connections: int
    active_connections: int
    idle_connections: int
    idle_in_transaction: int
    waiting_connections: int
    max_connections: int = 50
    utilization_percent: float
    pool_status: str  # healthy, warning, exhausted


class SlowQueriesInput(BaseModel):
    min_duration_ms: float = Field(default=100.0, ge=0.0, description="Minimum query duration threshold in milliseconds")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of slow queries to return")


class SlowQueryItem(BaseModel):
    pid: int
    duration_ms: float
    query: str
    state: str
    wait_event_type: Optional[str] = None
    wait_event: Optional[str] = None


class SlowQueriesResult(BaseModel):
    count: int
    queries: List[SlowQueryItem] = Field(default_factory=list)


class ActiveConnectionItem(BaseModel):
    pid: int
    usename: Optional[str] = "payment_user"
    client_addr: Optional[str] = "127.0.0.1"
    state: str
    wait_event_type: Optional[str] = None
    wait_event: Optional[str] = None
    duration_seconds: Optional[float] = 0.0
    query_preview: str


class ActiveConnectionsResult(BaseModel):
    count: int
    connections: List[ActiveConnectionItem] = Field(default_factory=list)


class ReadOnlyQueryInput(BaseModel):
    query: str = Field(description="Single-statement SELECT SQL query")
    row_limit: int = Field(default=20, ge=1, le=100, description="Maximum number of rows to return (clamped to 100)")
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0, description="Execution timeout limit")


class ReadOnlyQueryResult(BaseModel):
    query: str
    row_count: int
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    execution_duration_ms: float
    token_count: int
    truncated: bool = False
