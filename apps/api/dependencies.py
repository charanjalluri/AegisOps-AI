"""
AegisOps AI - API Security & Dependency Injection
Provides server-side operator authentication and authorization via FastAPI dependencies.
"""

from typing import Optional, Set
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from apps.mcp_incident.storage import InvestigationStorage


ALLOWED_OPERATOR_ROLES: Set[str] = {"sre", "admin", "oncall"}

# Shared storage instance for API routers (can connect to real DB or fallback to in-memory)
_global_storage: Optional[InvestigationStorage] = None


def get_storage() -> InvestigationStorage:
    """Returns the singleton or instance of InvestigationStorage for API routers."""
    global _global_storage
    if _global_storage is None:
        _global_storage = InvestigationStorage()
    return _global_storage


def set_storage(storage: Optional[InvestigationStorage]) -> None:
    """Sets the shared storage instance (useful for test isolation)."""
    global _global_storage
    _global_storage = storage


class OperatorContext(BaseModel):
    operator_id: str
    role: str = "sre"


async def require_operator_authorization(
    x_operator_id: Optional[str] = Header(default=None, alias="X-Operator-Id"),
    x_operator_role: Optional[str] = Header(default="sre", alias="X-Operator-Role"),
) -> OperatorContext:
    """
    Mandates operator identification and role validation.
    Raises HTTP 401 if operator_id is missing or whitespace.
    Raises HTTP 403 if operator_role is not in allowed roles.
    """
    if not x_operator_id or not x_operator_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-Operator-Id header is missing or empty.",
        )

    role_clean = (x_operator_role or "sre").strip().lower()
    if role_clean not in ALLOWED_OPERATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Operator role '{role_clean}' is not authorized. Allowed roles: {sorted(list(ALLOWED_OPERATOR_ROLES))}.",
        )

    return OperatorContext(operator_id=x_operator_id.strip(), role=role_clean)
