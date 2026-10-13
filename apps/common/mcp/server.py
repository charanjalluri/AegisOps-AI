"""
AegisOps AI - Shared Model Context Protocol (MCP) Server Engine
BaseMCPServer providing tool registration, schema introspection, timeout enforcement,
sliding-window rate limiting, and FastAPI routing.
"""

import inspect
import asyncio
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from pydantic import BaseModel

from apps.common.mcp.protocol import (
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPErrorCode,
    ToolCallResult,
    ToolDefinition,
    ToolInputSchema,
)
from apps.common.mcp.audit import AuditLogger
from apps.common.mcp.security import Sanitizer
from apps.common.mcp.budget import TokenBudgetGuard


class SlidingWindowRateLimiter:
    """Tracks invocation timestamps per (caller, tool) over a 60-second window."""

    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = window_seconds
        self.history: Dict[Tuple[str, str], deque] = {}

    def is_allowed(self, caller: str, tool_name: str, max_requests_per_minute: int) -> bool:
        now = time.time()
        key = (caller, tool_name)
        if key not in self.history:
            self.history[key] = deque()

        timestamps = self.history[key]
        cutoff = now - self.window_seconds

        # Prune older timestamps
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= max_requests_per_minute:
            return False

        timestamps.append(now)
        return True

    def reset(self):
        self.history.clear()


class RegisteredTool:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        input_schema: ToolInputSchema,
        timeout_seconds: float = 30.0,
        rate_limit_rpm: int = 120,
        is_mutation: bool = False,
        pydantic_model: Optional[Type[BaseModel]] = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.input_schema = input_schema
        self.timeout_seconds = timeout_seconds
        self.rate_limit_rpm = rate_limit_rpm
        self.is_mutation = is_mutation
        self.pydantic_model = pydantic_model

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema,
            timeout_seconds=self.timeout_seconds,
            rate_limit_rpm=self.rate_limit_rpm,
            is_mutation=self.is_mutation,
        )


def _schema_from_func(func: Callable, pydantic_model: Optional[Type[BaseModel]] = None) -> ToolInputSchema:
    """Generate ToolInputSchema from a Pydantic model or function signature."""
    if pydantic_model and issubclass(pydantic_model, BaseModel):
        model_schema = pydantic_model.model_json_schema()
        return ToolInputSchema(
            type="object",
            properties=model_schema.get("properties", {}),
            required=model_schema.get("required", []),
        )

    sig = inspect.signature(func)
    properties: Dict[str, Any] = {}
    required: List[str] = []

    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        param_type = "string"
        if param.annotation in type_mapping:
            param_type = type_mapping[param.annotation]
        elif inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
            # First param is a BaseModel
            sub_schema = param.annotation.model_json_schema()
            return ToolInputSchema(
                type="object",
                properties=sub_schema.get("properties", {}),
                required=sub_schema.get("required", []),
            )

        properties[param_name] = {"type": param_type}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return ToolInputSchema(type="object", properties=properties, required=required)


class BaseMCPServer:
    """
    Standard Base MCP Server providing tool registration, JSON-RPC 2.0 dispatch,
    timeout enforcement, and rate limiting.
    """

    def __init__(self, name: str, version: str = "0.1.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.tools: Dict[str, RegisteredTool] = {}
        self.rate_limiter = SlidingWindowRateLimiter()
        self.audit_logger = AuditLogger()

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        timeout_seconds: float = 30.0,
        rate_limit_rpm: int = 120,
        is_mutation: bool = False,
        pydantic_model: Optional[Type[BaseModel]] = None,
    ):
        """Decorator to register a tool with the MCP server."""

        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip() or f"Execute {tool_name}"
            input_schema = _schema_from_func(func, pydantic_model)

            registered = RegisteredTool(
                name=tool_name,
                description=tool_desc,
                func=func,
                input_schema=input_schema,
                timeout_seconds=timeout_seconds,
                rate_limit_rpm=rate_limit_rpm,
                is_mutation=is_mutation,
                pydantic_model=pydantic_model,
            )
            self.tools[tool_name] = registered
            return func

        return decorator

    def list_tools(self) -> List[ToolDefinition]:
        return [tool.to_definition() for tool in self.tools.values()]

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        caller: str = "default_agent",
    ) -> ToolCallResult:
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")

        tool = self.tools[name]

        # Rate limiting check
        if not self.rate_limiter.is_allowed(caller, name, tool.rate_limit_rpm):
            raise PermissionError(f"Rate limit exceeded for tool {name} ({tool.rate_limit_rpm} rpm)")

        # Prepare arguments
        kwargs = arguments.copy()
        if tool.pydantic_model:
            # Validate through Pydantic model
            model_instance = tool.pydantic_model(**kwargs)
            sig = inspect.signature(tool.func)
            if len(sig.parameters) == 1:
                call_args = (model_instance,)
                call_kwargs = {}
            else:
                call_args = ()
                call_kwargs = model_instance.model_dump()
        else:
            call_args = ()
            call_kwargs = kwargs

        # Execute with timeout
        start_time = time.time()
        status = "success"
        error_code = None
        result_output = None

        try:
            if asyncio.iscoroutinefunction(tool.func):
                result = await asyncio.wait_for(
                    tool.func(*call_args, **call_kwargs),
                    timeout=tool.timeout_seconds,
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool.func, *call_args, **call_kwargs),
                    timeout=tool.timeout_seconds,
                )

            if isinstance(result, ToolCallResult):
                call_res = result
            elif isinstance(result, (dict, list)):
                call_res = ToolCallResult.json_data(result)
            else:
                call_res = ToolCallResult.text(str(result))

            result_output = call_res
            return call_res

        except asyncio.TimeoutError:
            status = "timeout"
            error_code = MCPErrorCode.TOOL_TIMEOUT
            raise TimeoutError(f"Tool '{name}' execution exceeded timeout of {tool.timeout_seconds}s")
        except Exception as e:
            status = "error"
            error_code = MCPErrorCode.INTERNAL_ERROR
            raise e
        finally:
            duration_ms = (time.time() - start_time) * 1000.0
            if self.audit_logger:
                self.audit_logger.record(
                    tool_name=name,
                    caller=caller,
                    arguments=arguments,
                    duration_ms=duration_ms,
                    status=status,
                    error_code=error_code,
                    result_summary=str(result_output)[:200] if result_output else None,
                )

    async def handle_jsonrpc(
        self,
        request_data: Union[Dict[str, Any], str, JSONRPCRequest],
        caller: str = "default_agent",
    ) -> JSONRPCResponse:
        """Handle an inbound JSON-RPC 2.0 request."""
        # 1. Parse request
        if isinstance(request_data, JSONRPCRequest):
            req = request_data
        elif isinstance(request_data, dict):
            try:
                req = JSONRPCRequest(**request_data)
            except Exception as e:
                return JSONRPCResponse.failure(
                    id=request_data.get("id"),
                    code=MCPErrorCode.INVALID_REQUEST,
                    message=f"Invalid JSON-RPC request format: {str(e)}",
                )
        else:
            return JSONRPCResponse.failure(
                id=None,
                code=MCPErrorCode.PARSE_ERROR,
                message="Expected JSON object payload",
            )

        # 2. Dispatch method
        if req.method == "tools/list":
            tools_list = [t.model_dump() for t in self.list_tools()]
            return JSONRPCResponse.success(id=req.id, result={"tools": tools_list})

        elif req.method == "tools/call":
            params = req.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return JSONRPCResponse.failure(
                    id=req.id,
                    code=MCPErrorCode.INVALID_PARAMS,
                    message="Missing required parameter: 'name'",
                )

            if tool_name not in self.tools:
                return JSONRPCResponse.failure(
                    id=req.id,
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Unknown tool: '{tool_name}'",
                )

            try:
                tool_result = await self.call_tool(tool_name, arguments, caller=caller)
                return JSONRPCResponse.success(id=req.id, result=tool_result.model_dump())
            except TimeoutError as te:
                return JSONRPCResponse.failure(
                    id=req.id,
                    code=MCPErrorCode.TOOL_TIMEOUT,
                    message=str(te),
                )
            except PermissionError as pe:
                return JSONRPCResponse.failure(
                    id=req.id,
                    code=MCPErrorCode.RATE_LIMIT_EXCEEDED,
                    message=str(pe),
                )
            except Exception as ex:
                return JSONRPCResponse.failure(
                    id=req.id,
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Tool error: {str(ex)}",
                )

        else:
            return JSONRPCResponse.failure(
                id=req.id,
                code=MCPErrorCode.METHOD_NOT_FOUND,
                message=f"Method not supported: '{req.method}'",
            )

    def create_fastapi_router(self):
        """Create a FastAPI APIRouter exposing the MCP server endpoints."""
        from fastapi import APIRouter, Body

        router = APIRouter()

        @router.post("")
        @router.post("/")
        async def jsonrpc_endpoint(payload: Dict[str, Any] = Body(...)):
            response = await self.handle_jsonrpc(payload)
            return response.model_dump()

        @router.get("/health")
        async def health_endpoint():
            return {
                "server": self.name,
                "version": self.version,
                "status": "healthy",
                "registered_tools": len(self.tools),
            }

        @router.get("/tools")
        async def tools_endpoint():
            return {"tools": [t.model_dump() for t in self.list_tools()]}

        return router
