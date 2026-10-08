"""
AegisOps AI - Platform Core API Service
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.routers.health import router as health_router

app = FastAPI(
    title="AegisOps Platform API",
    description="Operational telemetry and autonomous incident intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)

@app.get("/")
async def root():
    return {
        "platform": "AegisOps AI",
        "version": "0.1.0",
        "phase": 1,
        "docs_url": "/docs",
        "health_url": "/health",
        "ready_url": "/ready",
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run("apps.api.main:app", host=host, port=port, reload=True)
