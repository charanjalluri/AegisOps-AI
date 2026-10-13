"""
Tests for apps.common.mcp.protocol
Verifies JSON-RPC 2.0 serialization, error codes, and MCP tool protocol models.
"""

import pytest
from apps.common.mcp.protocol import (
    MCPErrorCode,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    ToolDefinition,
    ToolInputSchema,
    ToolCallResult,
    ContentBlock,
)


def test_jsonrpc_request_serialization():
    req = JSONRPCRequest(
        id=1,
        method="tools/call",
        params={"name": "search_logs", "arguments": {"query": "error"}},
    )
    data = req.model_dump()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert data["method"] == "tools/call"
    assert data["params"]["name"] == "search_logs"


def test_jsonrpc_response_success():
    res = JSONRPCResponse.success(
        id=42,
        result={"tools": [{"name": "test_tool"}]},
    )
    assert res.jsonrpc == "2.0"
    assert res.id == 42
    assert res.error is None
    assert "tools" in res.result


def test_jsonrpc_response_failure():
    res = JSONRPCResponse.failure(
        id="req-123",
        code=MCPErrorCode.TOOL_TIMEOUT,
        message="Search took longer than 30s",
    )
    assert res.jsonrpc == "2.0"
    assert res.id == "req-123"
    assert res.result is None
    assert res.error is not None
    assert res.error.code == -32001
    assert res.error.message == "Search took longer than 30s"


def test_standard_error_codes():
    assert MCPErrorCode.PARSE_ERROR == -32700
    assert MCPErrorCode.METHOD_NOT_FOUND == -32601
    assert MCPErrorCode.RATE_LIMIT_EXCEEDED == -32002
    assert MCPErrorCode.POLICY_VIOLATION == -32003
    assert MCPErrorCode.TOKEN_BUDGET_EXCEEDED == -32004


def test_tool_definition_and_result():
    schema = ToolInputSchema(
        type="object",
        properties={"service": {"type": "string"}},
        required=["service"],
    )
    tool_def = ToolDefinition(
        name="get_service_logs",
        description="Fetch logs for a service",
        inputSchema=schema,
        timeout_seconds=15.0,
    )
    assert tool_def.name == "get_service_logs"
    assert tool_def.inputSchema.required == ["service"]
    assert tool_def.timeout_seconds == 15.0

    result = ToolCallResult.text("Found 5 log lines")
    assert len(result.content) == 1
    assert result.content[0].text == "Found 5 log lines"
    assert result.is_error is False

    json_result = ToolCallResult.json_data({"count": 5})
    assert len(json_result.content) == 1
    assert json_result.content[0].data == {"count": 5}
