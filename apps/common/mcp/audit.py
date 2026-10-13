"""
AegisOps AI - Shared MCP Audit Logger
Maintains sanitized audit records of all tool calls, inputs, durations, and outcomes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from apps.common.mcp.security import Sanitizer

logger = logging.getLogger("aegisops.mcp.audit")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    tool_name: str
    caller: str = "default_agent"
    sanitized_arguments: Dict[str, Any] = Field(default_factory=dict)
    sanitized_result_preview: Optional[str] = None
    execution_time_ms: float = 0.0
    status: str = "success"  # success, error, timeout, rejected
    error_code: Optional[int] = None


class AuditLogger:
    """Records sanitized invocation metadata for security compliance and debugging."""

    def __init__(self, max_in_memory: int = 1000):
        self.max_in_memory = max_in_memory
        self.entries: List[AuditEntry] = []

    def record(
        self,
        tool_name: str,
        caller: str,
        arguments: Dict[str, Any],
        duration_ms: float,
        status: str = "success",
        error_code: Optional[int] = None,
        result_summary: Optional[str] = None,
    ) -> AuditEntry:
        sanitized_args = Sanitizer.sanitize(arguments)
        preview = Sanitizer.sanitize(result_summary) if result_summary else None

        entry = AuditEntry(
            tool_name=tool_name,
            caller=caller,
            sanitized_arguments=sanitized_args,
            sanitized_result_preview=preview[:300] if preview else None,
            execution_time_ms=round(duration_ms, 2),
            status=status,
            error_code=error_code,
        )

        self.entries.append(entry)
        if len(self.entries) > self.max_in_memory:
            self.entries.pop(0)

        logger.info(
            f"MCP Tool Audit: tool={tool_name} caller={caller} status={status} duration={entry.execution_time_ms}ms"
        )
        return entry

    def get_entries(self, limit: int = 50) -> List[AuditEntry]:
        return self.entries[-limit:]

    def clear(self):
        self.entries.clear()
