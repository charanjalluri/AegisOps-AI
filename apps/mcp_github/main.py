"""
AegisOps AI - GitHub MCP Standalone Service & Stdio Runner
Provides HTTP JSON-RPC 2.0 endpoints on port 8004 and stdio streaming for agent integration.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.common.env import load_env_file
from apps.mcp_github.provider import BaseGitProvider, GitHubAPIProvider, LocalMockGitProvider
from apps.mcp_github.server import create_github_mcp_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aegisops.mcp_github")

git_provider: Optional[BaseGitProvider] = None
github_server = None


def get_git_provider() -> BaseGitProvider:
    load_env_file()
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    if token and not token.startswith("ghp_your_") and token.strip():
        logger.info(f"GitHub MCP using live GitHubAPIProvider for {owner or 'default'}/{repo or 'default'}")
        return GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo)
    logger.info("GitHub MCP using LocalMockGitProvider (offline deterministic mode)")
    return LocalMockGitProvider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global git_provider, github_server
    git_provider = get_git_provider()
    github_server = create_github_mcp_server(provider=git_provider)
    yield


app = FastAPI(
    title="AegisOps GitHub MCP Server",
    description="Read-only GitHub commit tracking, PR inspection, diff analysis, and release history MCP server",
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

# Standalone server instance for immediate router mount
standalone_server = create_github_mcp_server(provider=LocalMockGitProvider())
mcp_router = standalone_server.create_fastapi_router()
app.include_router(mcp_router, prefix="/mcp")


@app.get("/")
async def root():
    return {
        "service": "aegisops-github-mcp",
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
    parser = argparse.ArgumentParser(description="AegisOps GitHub MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode for direct agent pipe")
    parser.add_argument("--port", type=int, default=int(os.getenv("GITHUB_MCP_PORT", "8004")), help="HTTP port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="HTTP host")
    args = parser.parse_args()

    if args.stdio:
        server = create_github_mcp_server(provider=get_git_provider())
        asyncio.run(run_stdio(server))
    else:
        import uvicorn
        uvicorn.run("apps.mcp_github.main:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
