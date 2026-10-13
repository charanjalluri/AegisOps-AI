"""
AegisOps AI - Logs MCP Standalone Service & Stdio Runner
Provides HTTP JSON-RPC 2.0 endpoints on port 8002 and stdio streaming for agent integration.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional
import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.ingestion.database import get_connection_pool
from apps.mcp_logs.server import create_logs_mcp_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aegisops.mcp_logs")

db_pool: Optional[asyncpg.Pool] = None
logs_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, logs_server
    try:
        db_pool = await get_connection_pool("aegisops_db")
        logger.info("Logs MCP connected to PostgreSQL aegisops_db")
    except Exception as e:
        logger.warning(f"Logs MCP running without live PostgreSQL pool: {e}")
        db_pool = None

    logs_server = create_logs_mcp_server(pool=db_pool)
    yield
    if db_pool:
        await db_pool.close()
        logger.info("Logs MCP closed PostgreSQL pool")


app = FastAPI(
    title="AegisOps Logs MCP Server",
    description="Controlled read-only log search, error rate analytics, and window extraction MCP server",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize standalone server instance for immediate router mount
standalone_server = create_logs_mcp_server()
mcp_router = standalone_server.create_fastapi_router()
app.include_router(mcp_router, prefix="/mcp")

@app.get("/")
async def root():
    return {
        "service": "aegisops-logs-mcp",
        "version": "0.1.0",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "server": standalone_server.name,
        "registered_tools": len(standalone_server.tools),
    }

@app.get("/tools")
async def tools():
    return {"tools": [t.model_dump() for t in standalone_server.list_tools()]}


async def run_stdio(server):
    """Reads JSON-RPC lines from standard input and outputs responses to standard output."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            req_data = json.loads(line.decode("utf-8").strip())
            resp = await server.handle_jsonrpc(req_data)
            sys.stdout.write(resp.model_dump_json() + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="AegisOps Logs MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode for direct agent pipe")
    parser.add_argument("--port", type=int, default=int(os.getenv("LOGS_MCP_PORT", "8002")), help="HTTP port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="HTTP host")
    args = parser.parse_args()

    if args.stdio:
        server = create_logs_mcp_server()
        asyncio.run(run_stdio(server))
    else:
        import uvicorn
        uvicorn.run("apps.mcp_logs.main:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
