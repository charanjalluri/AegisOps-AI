"""
AegisOps AI - Platform Core API Service
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.routers.health import router as health_router
from apps.api.routers.incidents import router as incidents_router
from apps.api.routers.observability import router as observability_router
from apps.api.routers.governance import router as governance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically seed initial demo data if running as server outside pytest
    if not os.getenv("PYTEST_CURRENT_TEST"):
        try:
            from apps.api.seed import seed_demo_incidents
            await seed_demo_incidents()
        except Exception:
            pass
    yield


app = FastAPI(
    title="AegisOps Platform API",
    description="Operational telemetry and autonomous incident intelligence API",
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

app.include_router(health_router)
app.include_router(incidents_router)
app.include_router(observability_router)
app.include_router(governance_router)

@app.get("/")
async def root():
    return {
        "platform": "AegisOps AI",
        "version": "0.1.0",
        "phase": 6,
        "docs_url": "/docs",
        "health_url": "/health",
        "ready_url": "/ready",
        "incidents_url": "/api/incidents",
        "observability_url": "/api/observability/status",
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run("apps.api.main:app", host=host, port=port, reload=True)
