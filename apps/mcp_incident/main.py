"""
AegisOps AI - Incident MCP Standalone Service & Stdio Runner
Provides HTTP JSON-RPC 2.0 endpoints on port 8005 and stdio streaming for agent integration.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional
from aiokafka import AIOKafkaProducer
import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.ingestion.database import get_connection_pool
from apps.mcp_incident.server import create_incident_mcp_server
from apps.mcp_incident.storage import InvestigationStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aegisops.mcp_incident")

db_pool: Optional[asyncpg.Pool] = None
kafka_producer: Optional[AIOKafkaProducer] = None
storage_instance: Optional[InvestigationStorage] = None
incident_server = None


async def emit_kafka_event(topic: str, payload: dict):
    """Publishes operational and AI event messages to Kafka topics."""
    if kafka_producer:
        try:
            msg_bytes = json.dumps(payload, default=str).encode("utf-8")
            await kafka_producer.send_and_wait(topic, msg_bytes)
            logger.info(f"Published event to Kafka topic '{topic}'")
        except Exception as e:
            logger.warning(f"Failed to publish event to topic '{topic}': {e}")
    else:
        logger.debug(f"[Offline] Event '{topic}': {payload}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, kafka_producer, storage_instance, incident_server

    # 1. PostgreSQL pool
    try:
        db_pool = await get_connection_pool("aegisops_db")
        storage_instance = InvestigationStorage(pool=db_pool)
        await storage_instance.init_schema()
        logger.info("Incident MCP connected to PostgreSQL aegisops_db and verified schema")
    except Exception as e:
        logger.warning(f"Incident MCP running with in-memory storage (PostgreSQL pool unavailable): {e}")
        db_pool = None
        storage_instance = InvestigationStorage()

    # 2. Kafka producer
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        kafka_producer = AIOKafkaProducer(bootstrap_servers=kafka_bootstrap)
        await kafka_producer.start()
        logger.info(f"Incident MCP connected to Kafka at {kafka_bootstrap}")
    except Exception as e:
        logger.warning(f"Incident MCP running without live Kafka producer: {e}")
        kafka_producer = None

    incident_server = create_incident_mcp_server(
        storage=storage_instance,
        event_emitter=emit_kafka_event,
    )
    yield

    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Incident MCP stopped Kafka producer")
    if db_pool:
        await db_pool.close()
        logger.info("Incident MCP closed PostgreSQL pool")


app = FastAPI(
    title="AegisOps Incident MCP Server",
    description="Transactional incident lifecycle, evidence chaining, hypotheses, and action proposals MCP server",
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
standalone_server = create_incident_mcp_server(
    storage=InvestigationStorage(),
    event_emitter=emit_kafka_event,
)
mcp_router = standalone_server.create_fastapi_router()
app.include_router(mcp_router, prefix="/mcp")


@app.get("/")
async def root():
    return {
        "service": "aegisops-incident-mcp",
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
    parser = argparse.ArgumentParser(description="AegisOps Incident MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode for direct agent pipe")
    parser.add_argument("--port", type=int, default=int(os.getenv("INCIDENT_MCP_PORT", "8005")), help="HTTP port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="HTTP host")
    args = parser.parse_args()

    if args.stdio:
        server = create_incident_mcp_server(storage=InvestigationStorage(), event_emitter=emit_kafka_event)
        asyncio.run(run_stdio(server))
    else:
        import uvicorn
        uvicorn.run("apps.mcp_incident.main:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
