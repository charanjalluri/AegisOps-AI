"""
AegisOps AI - Shared Model Context Protocol (MCP) Framework
Standard JSON-RPC 2.0 and MCP Protocol Message Models & Error Codes.
"""

from enum import IntEnum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPErrorCode(IntEnum):
    # Standard JSON-RPC 2.0 error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # AegisOps MCP domain error codes
    TOOL_TIMEOUT = -32001
    RATE_LIMIT_EXCEEDED = -32002
    POLICY_VIOLATION = -32003
    TOKEN_BUDGET_EXCEEDED = -32004
    RESOURCE_NOT_FOUND = -32005


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

    @classmethod
    def create(
        cls,
        code: Union[MCPErrorCode, int],
        message: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> "JSONRPCError":
        default_messages = {
            MCPErrorCode.PARSE_ERROR: "Parse error",
            MCPErrorCode.INVALID_REQUEST: "Invalid Request",
            MCPErrorCode.METHOD_NOT_FOUND: "Method not found",
            MCPErrorCode.INVALID_PARAMS: "Invalid params",
            MCPErrorCode.INTERNAL_ERROR: "Internal error",
            MCPErrorCode.TOOL_TIMEOUT: "Tool execution timed out",
            MCPErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded",
            MCPErrorCode.POLICY_VIOLATION: "Policy violation: action rejected",
            MCPErrorCode.TOKEN_BUDGET_EXCEEDED: "Token budget exceeded",
            MCPErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
        }
        msg = message or default_messages.get(code, "Unknown error")
        return cls(code=int(code), message=msg, data=data)


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None

    @classmethod
    def success(cls, id: Optional[Union[str, int]], result: Any) -> "JSONRPCResponse":
        return cls(id=id, result=result, error=None)

    @classmethod
    def failure(
        cls,
        id: Optional[Union[str, int]],
        code: Union[MCPErrorCode, int],
        message: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> "JSONRPCResponse":
        return cls(id=id, result=None, error=JSONRPCError.create(code, message, data))


class ToolInputSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: ToolInputSchema
    timeout_seconds: float = 30.0
    rate_limit_rpm: int = 120
    is_mutation: bool = False


class ContentBlock(BaseModel):
    type: str = "text"  # text, json, or resource
    text: Optional[str] = None
    data: Optional[Any] = None


class ToolCallResult(BaseModel):
    content: List[ContentBlock] = Field(default_factory=list)
    is_error: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def text(cls, text: str, is_error: bool = False, metadata: Optional[Dict[str, Any]] = None) -> "ToolCallResult":
        return cls(
            content=[ContentBlock(type="text", text=text)],
            is_error=is_error,
            metadata=metadata or {},
        )

    @classmethod
    def json_data(cls, data: Any, is_error: bool = False, metadata: Optional[Dict[str, Any]] = None) -> "ToolCallResult":
        import json
        text_rep = json.dumps(data, default=str) if not isinstance(data, str) else data
        return cls(
            content=[ContentBlock(type="text", text=text_rep, data=data)],
            is_error=is_error,
            metadata=metadata or {},
        )
