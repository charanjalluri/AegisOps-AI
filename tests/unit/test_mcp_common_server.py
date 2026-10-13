"""
Tests for apps.common.mcp.server
Verifies BaseMCPServer tool decorator, schema generation, async execution,
timeout enforcement, sliding-window rate limiting, and JSON-RPC dispatch.
"""

import asyncio
import pytest
from pydantic import BaseModel, Field

from apps.common.mcp.server import BaseMCPServer
from apps.common.mcp.protocol import MCPErrorCode, ToolCallResult


class SimpleInput(BaseModel):
    service: str = Field(..., description="Service name")
    limit: int = Field(default=10, description="Max records")


@pytest.mark.anyio
async def test_tool_registration_and_list():
    server = BaseMCPServer(name="test-server", version="1.0.0")

    @server.tool(name="ping", description="Ping test tool")
    def ping():
        return "pong"

    @server.tool(name="query_logs", description="Query logs with model", pydantic_model=SimpleInput)
    async def query_logs(inp: SimpleInput):
        return {"service": inp.service, "found": inp.limit}

    tools = server.list_tools()
    assert len(tools) == 2

    tool_names = [t.name for t in tools]
    assert "ping" in tool_names
    assert "query_logs" in tool_names

    # Check Pydantic schema generation
    query_tool = next(t for t in tools if t.name == "query_logs")
    assert "service" in query_tool.inputSchema.properties
    assert "limit" in query_tool.inputSchema.properties
    assert "service" in query_tool.inputSchema.required


@pytest.mark.anyio
async def test_handle_jsonrpc_tools_list():
    server = BaseMCPServer(name="test-server")

    @server.tool(name="hello")
    def hello(name: str = "world"):
        return f"hello {name}"

    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    resp = await server.handle_jsonrpc(req)

    assert resp.error is None
    assert resp.id == 1
    assert "tools" in resp.result
    assert len(resp.result["tools"]) == 1
    assert resp.result["tools"][0]["name"] == "hello"


@pytest.mark.anyio
async def test_handle_jsonrpc_tools_call_success():
    server = BaseMCPServer(name="test-server")

    @server.tool(name="calculate")
    def calculate(x: int, y: int):
        return x + y

    req = {
        "jsonrpc": "2.0",
        "id": "c-1",
        "method": "tools/call",
        "params": {"name": "calculate", "arguments": {"x": 10, "y": 32}},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.id == "c-1"
    assert resp.result["content"][0]["text"] == "42"


@pytest.mark.anyio
async def test_handle_jsonrpc_timeout_enforcement():
    server = BaseMCPServer(name="test-server")

    @server.tool(name="slow_tool", timeout_seconds=0.05)
    async def slow_tool():
        await asyncio.sleep(0.2)
        return "finished"

    req = {
        "jsonrpc": "2.0",
        "id": "timeout-1",
        "method": "tools/call",
        "params": {"name": "slow_tool", "arguments": {}},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.result is None
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.TOOL_TIMEOUT


@pytest.mark.anyio
async def test_handle_jsonrpc_rate_limiting():
    server = BaseMCPServer(name="test-server")

    @server.tool(name="limited_tool", rate_limit_rpm=2)
    def limited_tool():
        return "ok"

    # Call 1: Allowed
    r1 = await server.handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "limited_tool", "arguments": {}}},
        caller="agent-1",
    )
    assert r1.error is None

    # Call 2: Allowed
    r2 = await server.handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "limited_tool", "arguments": {}}},
        caller="agent-1",
    )
    assert r2.error is None

    # Call 3: Exceeded
    r3 = await server.handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "limited_tool", "arguments": {}}},
        caller="agent-1",
    )
    assert r3.error is not None
    assert r3.error.code == MCPErrorCode.RATE_LIMIT_EXCEEDED


@pytest.mark.anyio
async def test_handle_jsonrpc_method_not_found():
    server = BaseMCPServer(name="test-server")
    req = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {"name": "unknown_tool", "arguments": {}},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.METHOD_NOT_FOUND
