import pytest
from httpx import AsyncClient, ASGITransport

from apps.payment_service.main import app
from apps.payment_service.database import db

@pytest.fixture(autouse=True)
async def clean_db():
    await db.reset()
    yield
    await db.reset()

@pytest.mark.anyio
async def test_process_payment_success():
    payload = {
        "account_id": "acc-9901",
        "amount": 149.99,
        "currency": "USD",
        "description": "Subscription charge",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/payments", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == "acc-9901"
    assert data["amount"] == 149.99
    assert data["status"] == "completed"
    assert data["latency_ms"] > 0
    assert "payment_id" in data

@pytest.mark.anyio
async def test_list_payments():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create 2 transactions
        await client.post("/payments", json={"account_id": "acc-1", "amount": 25.0, "currency": "USD"})
        await client.post("/payments", json={"account_id": "acc-2", "amount": 75.0, "currency": "USD"})

        response = await client.get("/payments")
    
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["account_id"] in ("acc-1", "acc-2")

@pytest.mark.anyio
async def test_payment_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "payment-service"
    assert data["version"] == "v2.8.0"
    assert data["status"] == "healthy"
    assert data["db_connected"] is True
    assert data["pool_utilization_pct"] <= 50.0

@pytest.mark.anyio
async def test_payment_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/payments", json={"account_id": "acc-metrics", "amount": 50.0, "currency": "USD"})
        response = await client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "payment-service"
    assert data["total_transactions"] >= 1
    assert data["successful_transactions"] >= 1
    assert data["error_rate_pct"] == 0.0
