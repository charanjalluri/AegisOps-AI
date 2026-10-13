"""
AegisOps AI - Investigation Budget Controller (REASON-04)
Enforces strict execution limits to prevent infinite agent query loops:
- Maximum tool calls (default 20)
- Wall-clock timeout (default 300s / 5 minutes)
- Expensive operations cap (default 5)
"""

import time
from typing import Optional


class InvestigationBudget:
    """
    Enforces computational and temporal safety bounds during autonomous investigations.
    """

    def __init__(
        self,
        max_tool_calls: int = 20,
        timeout_seconds: float = 300.0,
        max_expensive_operations: int = 5,
    ):
        self.max_tool_calls = max_tool_calls
        self.timeout_seconds = timeout_seconds
        self.max_expensive_operations = max_expensive_operations

        self.tool_call_count = 0
        self.expensive_operation_count = 0
        self.start_time = time.time()
        self._exhausted_reason: Optional[str] = None

    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def remaining_calls(self) -> int:
        return max(0, self.max_tool_calls - self.tool_call_count)

    def is_exhausted(self) -> bool:
        if self._exhausted_reason:
            return True

        if self.tool_call_count >= self.max_tool_calls:
            self._exhausted_reason = f"Maximum tool call budget ({self.max_tool_calls}) reached."
            return True

        if self.expensive_operation_count >= self.max_expensive_operations:
            self._exhausted_reason = f"Maximum expensive operations ({self.max_expensive_operations}) reached."
            return True

        if self.elapsed_seconds() >= self.timeout_seconds:
            self._exhausted_reason = f"Investigation execution timeout ({self.timeout_seconds}s) exceeded."
            return True

        return False

    def reason_for_exhaustion(self) -> Optional[str]:
        self.is_exhausted()
        return self._exhausted_reason

    def record_tool_call(self, tool_name: str, is_expensive: bool = False):
        """Records a tool invocation and checks safety bounds."""
        if self.is_exhausted():
            raise RuntimeError(f"Cannot execute tool '{tool_name}': {self._exhausted_reason}")

        self.tool_call_count += 1
        if is_expensive:
            self.expensive_operation_count += 1

        # Check if this call triggered exhaustion
        self.is_exhausted()
