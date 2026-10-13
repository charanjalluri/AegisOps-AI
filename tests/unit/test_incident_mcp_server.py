"""
Unit tests for Incident MCP Server JSON-RPC and HTTP API endpoints.
Verifies tool discovery, tool execution, transactional memory updates, and HTTP routing.
"""

import httpx
import pytest
from httpx import ASGITransport

from apps.mcp_incident.main import app
from apps.mcp_incident.server import create_incident_mcp_server
from apps.mcp_incident.storage import InvestigationStorage


@pytest.mark.anyio
async def test_incident_mcp_tools_list():
    server = create_incident_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/list",
        "params": {},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None
    tools = resp.result["tools"]
    tool_names = [t["name"] for t in tools]
    assert len(tools) == 7
    assert "create_incident" in tool_names
    assert "update_incident" in tool_names
    assert "add_evidence" in tool_names
    assert "add_hypothesis" in tool_names
    assert "create_action_proposal" in tool_names
    assert "close_incident" in tool_names
    assert "get_incident" in tool_names


@pytest.mark.anyio
async def test_incident_mcp_call_create_and_query():
    storage = InvestigationStorage()
    server = create_incident_mcp_server(storage=storage)

    # 1. create_incident
    req_create = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/call",
        "params": {
            "name": "create_incident",
            "arguments": {
                "incident_id": "inc-rpc-1",
                "title": "Payment gateway latency surge",
                "service": "payment-service",
                "severity": "SEV-1",
            },
        },
    }
    resp_create = await server.handle_jsonrpc(req_create)
    assert resp_create.error is None
    assert resp_create.result["is_error"] is False
    assert resp_create.result["content"][0]["data"]["incident_id"] == "inc-rpc-1"

    # 2. add_evidence
    req_ev = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {
            "name": "add_evidence",
            "arguments": {
                "incident_id": "inc-rpc-1",
                "source_tool": "mcp_database.get_connection_pool",
                "signal_type": "pool_exhaustion",
                "confidence_weight": 0.95,
                "raw_data": {"active": 50, "token": "secret123"},
                "interpretation": "Pool exhausted",
            },
        },
    }
    resp_ev = await server.handle_jsonrpc(req_ev)
    assert resp_ev.error is None
    data_ev = resp_ev.result["content"][0]["data"]
    assert data_ev["raw_data"]["token"] == "[REDACTED]"

    # 3. add_hypothesis
    req_hypo = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "tools/call",
        "params": {
            "name": "add_hypothesis",
            "arguments": {
                "incident_id": "inc-rpc-1",
                "title": "Connection leak in v2.8.1",
                "confidence_score": 0.9,
                "supporting_evidence": [data_ev["id"]],
            },
        },
    }
    resp_hypo = await server.handle_jsonrpc(req_hypo)
    assert resp_hypo.error is None
    hypo_id = resp_hypo.result["content"][0]["data"]["id"]

    # 4. create_action_proposal
    req_prop = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "tools/call",
        "params": {
            "name": "create_action_proposal",
            "arguments": {
                "incident_id": "inc-rpc-1",
                "action_type": "rollback_deployment",
                "parameters": {"target_version": "v2.8.0"},
                "risk_level": "HIGH",
            },
        },
    }
    resp_prop = await server.handle_jsonrpc(req_prop)
    assert resp_prop.error is None

    # 5. close_incident
    req_close = {
        "jsonrpc": "2.0",
        "id": "6",
        "method": "tools/call",
        "params": {
            "name": "close_incident",
            "arguments": {
                "incident_id": "inc-rpc-1",
                "root_cause": "v2.8.1 leak commit c0ffee1",
                "winning_hypothesis_id": hypo_id,
            },
        },
    }
    resp_close = await server.handle_jsonrpc(req_close)
    assert resp_close.error is None
    assert resp_close.result["content"][0]["data"]["status"] == "resolved"

    # 6. get_incident
    req_get = {
        "jsonrpc": "2.0",
        "id": "7",
        "method": "tools/call",
        "params": {
            "name": "get_incident",
            "arguments": {"incident_id": "inc-rpc-1"},
        },
    }
    resp_get = await server.handle_jsonrpc(req_get)
    assert resp_get.error is None
    inc_data = resp_get.result["content"][0]["data"]
    assert len(inc_data["evidence"]) == 1
    assert len(inc_data["hypotheses"]) == 1
    assert len(inc_data["action_proposals"]) == 1


@pytest.mark.anyio
async def test_incident_mcp_call_error_handling():
    server = create_incident_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "8",
        "method": "tools/call",
        "params": {
            "name": "update_incident",
            "arguments": {
                "incident_id": "non-existent-inc",
                "status": "resolved",
            },
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is not None
    assert "not found" in resp.error.message


@pytest.mark.anyio
async def test_incident_mcp_http_endpoints():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "healthy"
        assert r_health.json()["registered_tools"] == 7

        # Tools list
        r_tools = await client.get("/tools")
        assert r_tools.status_code == 200
        assert len(r_tools.json()["tools"]) == 7

        # POST /mcp JSON-RPC
        rpc_payload = {
            "jsonrpc": "2.0",
            "id": "http-inc-1",
            "method": "tools/call",
            "params": {
                "name": "create_incident",
                "arguments": {
                    "incident_id": "inc-http-1",
                    "title": "HTTP created incident",
                    "service": "payment-service",
                },
            },
        }
        r_rpc = await client.post("/mcp", json=rpc_payload)
        assert r_rpc.status_code == 200
        resp_json = r_rpc.json()
        assert resp_json["id"] == "http-inc-1"
        assert not resp_json["result"]["is_error"]
