"""
AegisOps AI - Shared MCP Token Budget Guard & Pagination
Protects LLM context windows from token blowup and provides standardized pagination.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Union


class TokenBudgetGuard:
    """Estimates tokens and enforces budget constraints on MCP tool responses."""

    DEFAULT_MAX_TOKENS = 4000
    CHARS_PER_TOKEN = 4

    @classmethod
    def estimate_tokens(cls, content: Union[str, Any]) -> int:
        if isinstance(content, str):
            text = content
        else:
            try:
                text = json.dumps(content, default=str)
            except Exception:
                text = str(content)
        return max(1, len(text) // cls.CHARS_PER_TOKEN)

    @classmethod
    def is_within_budget(cls, content: Any, max_tokens: int = DEFAULT_MAX_TOKENS) -> bool:
        return cls.estimate_tokens(content) <= max_tokens

    @classmethod
    def paginate_records(
        cls,
        items: List[Any],
        cursor: Optional[str] = None,
        limit: int = 50,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Dict[str, Any]:
        """
        Paginates a list of records respecting both item count limit and token budget.
        """
        clamped_limit = max(1, min(limit, 200))

        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except ValueError:
                start_idx = 0

        total_items = len(items)
        if start_idx >= total_items:
            return {
                "items": [],
                "count": 0,
                "total": total_items,
                "next_cursor": None,
                "truncated_by_budget": False,
                "estimated_tokens": 0,
            }

        selected: List[Any] = []
        current_tokens = 0
        truncated_by_budget = False
        current_idx = start_idx

        while current_idx < total_items and len(selected) < clamped_limit:
            candidate = items[current_idx]
            cand_tokens = cls.estimate_tokens(candidate)

            if current_tokens + cand_tokens > max_tokens and len(selected) > 0:
                truncated_by_budget = True
                break

            selected.append(candidate)
            current_tokens += cand_tokens
            current_idx += 1

        next_cursor = str(current_idx) if current_idx < total_items else None

        return {
            "items": selected,
            "count": len(selected),
            "total": total_items,
            "next_cursor": next_cursor,
            "truncated_by_budget": truncated_by_budget,
            "estimated_tokens": current_tokens,
        }
