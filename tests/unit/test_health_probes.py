import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from apps.api.main import app

@pytest.mark.anyio
async def test_health_liveness_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aegisops-api"
    assert data["phase"] == 1

@pytest.mark.anyio
async def test_ready_endpoint_hard_deps_up_soft_deps_down():
    """
    Key architectural test: Readiness probe must return 200 OK when Postgres and Kafka
    are healthy, even if soft dependencies (Qdrant, n8n) are unavailable.
    """
    mock_postgres = {"status": "healthy", "database": "aegisops_db", "required": True}
    mock_kafka = {"status": "healthy", "bootstrap_servers": "localhost:29092", "required": True}
    mock_qdrant = {"status": "unavailable", "url": "http://localhost:6333", "required": False}
    mock_n8n = {"status": "unavailable", "url": "http://localhost:5678", "required": False}

    with patch("apps.api.routers.health.check_postgres", return_value=mock_postgres), \
         patch("apps.api.routers.health.check_kafka", return_value=mock_kafka), \
         patch("apps.api.routers.health.check_qdrant", return_value=mock_qdrant), \
         patch("apps.api.routers.health.check_n8n", return_value=mock_n8n):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == 200, "Readiness must return 200 when hard dependencies are up"
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["postgres"]["status"] == "healthy"
        assert data["dependencies"]["kafka"]["status"] == "healthy"
        assert data["dependencies"]["qdrant"]["status"] == "unavailable"
        assert data["dependencies"]["n8n"]["status"] == "unavailable"

@pytest.mark.anyio
async def test_ready_endpoint_hard_dep_down():
    """
    Readiness probe must return 503 when a hard dependency (e.g. Postgres) is unreachable.
    """
    mock_postgres = {"status": "unreachable", "database": "aegisops_db", "required": True, "error": "timeout"}
    mock_kafka = {"status": "healthy", "bootstrap_servers": "localhost:29092", "required": True}

    with patch("apps.api.routers.health.check_postgres", return_value=mock_postgres), \
         patch("apps.api.routers.health.check_kafka", return_value=mock_kafka), \
         patch("apps.api.routers.health.check_qdrant", return_value={"status": "available", "required": False}), \
         patch("apps.api.routers.health.check_n8n", return_value={"status": "available", "required": False}):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == 503, "Readiness must return 503 when Postgres is down"
        data = response.json()
        assert data["status"] == "unready"
        assert data["dependencies"]["postgres"]["status"] == "unreachable"

@pytest.mark.anyio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["platform"] == "AegisOps AI"
