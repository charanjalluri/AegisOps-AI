"""
AegisOps AI - Logs MCP Tool Input & Output Contracts
Strongly typed Pydantic V2 models for log introspection, error rate analytics, and window extraction.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    id: str
    timestamp: datetime
    service: str
    level: str
    message: str
    environment: Optional[str] = "development"
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchLogsInput(BaseModel):
    service: Optional[str] = Field(default=None, description="Filter logs by service name")
    level: Optional[str] = Field(default=None, description="Filter logs by level (INFO, WARNING, ERROR, CRITICAL)")
    pattern: Optional[str] = Field(default=None, description="Substring or pattern match in log message")
    start_time: Optional[datetime] = Field(default=None, description="Inclusive start timestamp")
    end_time: Optional[datetime] = Field(default=None, description="Inclusive end timestamp")
    limit: int = Field(default=50, ge=1, le=200, description="Max logs to return (1-200)")
    cursor: Optional[str] = Field(default=None, description="Pagination cursor")


class LogsQueryResult(BaseModel):
    logs: List[LogRecord] = Field(default_factory=list)
    count: int = 0
    next_cursor: Optional[str] = None
    truncated_by_budget: bool = False
    estimated_tokens: int = 0


class GetServiceLogsInput(BaseModel):
    service: str = Field(..., description="Target service name")
    limit: int = Field(default=50, ge=1, le=200, description="Max logs to return (1-200)")
    min_level: str = Field(default="INFO", description="Minimum log level threshold")


class GetErrorRateInput(BaseModel):
    service: str = Field(..., description="Target service name")
    interval_seconds: int = Field(default=60, ge=10, le=3600, description="Bucket interval in seconds")
    window_minutes: int = Field(default=30, ge=1, le=1440, description="Lookback window in minutes")
    end_time: Optional[datetime] = Field(default=None, description="Anchor end timestamp, defaults to now")


class ErrorRateBucket(BaseModel):
    start_time: datetime
    end_time: datetime
    total_logs: int
    error_logs: int
    error_percentage: float


class ErrorRateResult(BaseModel):
    service: str
    buckets: List[ErrorRateBucket] = Field(default_factory=list)
    overall_error_rate_pct: float = 0.0
    total_logs: int = 0
    total_errors: int = 0


class GetCorrelatedErrorsInput(BaseModel):
    service: str = Field(..., description="Target service name")
    error_pattern: str = Field(..., description="Error message substring or keyword (e.g. ConnectionPoolTimeout)")
    window_seconds: int = Field(default=60, ge=5, le=300, description="Correlation window size before/after errors")


class CorrelatedErrorsResult(BaseModel):
    service: str
    error_pattern: str
    matching_errors_count: int
    correlated_events: List[Dict[str, Any]] = Field(default_factory=list)


class GetLogsAroundEventInput(BaseModel):
    timestamp: datetime = Field(..., description="Center anchor timestamp of the event")
    window_seconds: int = Field(default=60, ge=5, le=300, description="Lookback and lookforward window in seconds")
    service: Optional[str] = Field(default=None, description="Optional service filter")
    limit: int = Field(default=50, ge=1, le=200, description="Max logs to return (1-200)")


class LogsAroundEventResult(BaseModel):
    target_timestamp: datetime
    window_seconds: int
    service: Optional[str] = None
    logs_before: List[LogRecord] = Field(default_factory=list)
    logs_after: List[LogRecord] = Field(default_factory=list)
    total_logs: int = 0
