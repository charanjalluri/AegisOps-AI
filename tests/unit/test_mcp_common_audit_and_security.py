"""
Tests for apps.common.mcp.security, audit, and budget
Verifies credential redaction, structured audit logging, token budgeting, and pagination.
"""

import pytest
from apps.common.mcp.security import Sanitizer
from apps.common.mcp.audit import AuditLogger
from apps.common.mcp.budget import TokenBudgetGuard
from apps.common.mcp.server import BaseMCPServer


def test_sanitizer_redacts_sensitive_dict_keys():
    payload = {
        "user": "alice",
        "password": "supersecretpassword123",
        "api_key": "ak_live_abcdef1234567890",
        "nested": {
            "token": "ghp_1234567890abcdef",
            "safe_field": "public_data",
        },
    }
    sanitized = Sanitizer.sanitize(payload)

    assert sanitized["user"] == "alice"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "public_data"


def test_sanitizer_redacts_strings_and_uris():
    uri = "postgresql://user:secretpassword@postgres:5432/aegisops_db"
    assert "secretpassword" not in Sanitizer.sanitize(uri)
    assert "[REDACTED]" in Sanitizer.sanitize(uri)

    auth = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tokenpayload"
    assert "tokenpayload" not in Sanitizer.sanitize(auth)
    assert "[REDACTED]" in Sanitizer.sanitize(auth)


def test_audit_logger_records_sanitized_entries():
    logger = AuditLogger()
    entry = logger.record(
        tool_name="connect_db",
        caller="test_agent",
        arguments={"db_password": "mypassword", "host": "localhost"},
        duration_ms=45.2,
        status="success",
        result_summary="Connected to database successfully",
    )

    assert entry.tool_name == "connect_db"
    assert entry.caller == "test_agent"
    assert entry.sanitized_arguments["db_password"] == "[REDACTED]"
    assert entry.sanitized_arguments["host"] == "localhost"
    assert entry.execution_time_ms == 45.2
    assert entry.status == "success"

    entries = logger.get_entries()
    assert len(entries) == 1
    assert entries[0] == entry


def test_token_budget_guard_estimates_tokens():
    text = "a" * 400
    estimated = TokenBudgetGuard.estimate_tokens(text)
    assert estimated == 100

    obj = {"key": "value" * 10}
    est_obj = TokenBudgetGuard.estimate_tokens(obj)
    assert est_obj > 0
    assert TokenBudgetGuard.is_within_budget(obj, max_tokens=1000) is True


def test_token_budget_guard_paginate_records():
    # 20 items of ~40 characters each (approx 10 tokens each)
    items = [{"id": i, "data": "x" * 40} for i in range(20)]

    # Limit 5
    page1 = TokenBudgetGuard.paginate_records(items, cursor="0", limit=5, max_tokens=1000)
    assert page1["count"] == 5
    assert page1["next_cursor"] == "5"
    assert page1["total"] == 20
    assert page1["truncated_by_budget"] is False

    # Budget cap: max 30 tokens should only take 2 items
    page_budget = TokenBudgetGuard.paginate_records(items, cursor="0", limit=10, max_tokens=25)
    assert page_budget["count"] < 10
    assert page_budget["truncated_by_budget"] is True


@pytest.mark.anyio
async def test_server_audit_logger_integration():
    server = BaseMCPServer(name="audit-server")

    @server.tool(name="login")
    def login(username: str, password: str):
        return f"Welcome {username}"

    req = {
        "jsonrpc": "2.0",
        "id": "aud-1",
        "method": "tools/call",
        "params": {
            "name": "login",
            "arguments": {"username": "admin", "password": "supersecretpassword"},
        },
    }
    resp = await server.handle_jsonrpc(req, caller="test_user")
    assert resp.error is None

    # Check that audit log has entry with redacted password
    entries = server.audit_logger.get_entries()
    assert len(entries) == 1
    assert entries[0].tool_name == "login"
    assert entries[0].sanitized_arguments["password"] == "[REDACTED]"
    assert entries[0].sanitized_arguments["username"] == "admin"
