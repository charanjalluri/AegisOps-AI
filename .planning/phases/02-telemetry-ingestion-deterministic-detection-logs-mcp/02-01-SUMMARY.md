# Plan 02-01 Summary: Shared MCP Framework (mcp_common)

**Executed:** 2026-10-10
**Status:** Completed
**Requirements Covered:** MCP-01
**Tests Passing:** 17/17 Plan 02-01 unit tests (46/46 overall suite passing)

## What Was Built
1. **MCP Protocol Models & Error Codes (`apps/common/mcp/protocol.py`)**:
   - Standard JSON-RPC 2.0 message schemas (`JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCError`).
   - Standard error codes (`PARSE_ERROR`, `INVALID_REQUEST`, `METHOD_NOT_FOUND`, `INVALID_PARAMS`, `INTERNAL_ERROR`) and AegisOps domain codes (`TOOL_TIMEOUT`, `RATE_LIMIT_EXCEEDED`, `POLICY_VIOLATION`, `TOKEN_BUDGET_EXCEEDED`).
   - MCP tool models: `ToolDefinition`, `ToolInputSchema`, `ContentBlock`, `ToolCallResult`.

2. **BaseMCPServer Engine (`apps/common/mcp/server.py`)**:
   - `@server.tool` decorator supporting both sync and async functions, automatic schema generation from function signatures and Pydantic models.
   - Async invocation with hard timeout enforcement (`asyncio.wait_for`).
   - Sliding-window rate limiter per tool and caller.
   - FastAPI APIRouter generator mounting JSON-RPC 2.0 endpoint, healthcheck, and tool catalog.

3. **Security, Audit & Token Budgeting (`apps/common/mcp/security.py`, `audit.py`, `budget.py`)**:
   - `Sanitizer`: recursive credential/secret masking for passwords, bearer tokens, API keys, and connection strings.
   - `AuditLogger`: structured in-memory and stdout audit records capturing sanitized arguments, durations, and statuses.
   - `TokenBudgetGuard`: token estimation heuristic and budget-enforcing pagination helper protecting LLMs from context window exhaustion.

## Verification
- `pytest tests/unit/test_mcp_common_protocol.py tests/unit/test_mcp_common_server.py tests/unit/test_mcp_common_audit_and_security.py -v` (17/17 passed in 0.41s).
