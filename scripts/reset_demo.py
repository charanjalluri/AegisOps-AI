#!/usr/bin/env python3
"""
AegisOps AI - Demo State Reset Script (make reset-demo)
Truncates demo transactions, resets test incidents, and resets payment-service simulator
to nominal v2.8.0 baseline without destroying Docker infrastructure.
"""

import asyncio
import logging
import os
import sys

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reset_demo")


async def reset_demo_database():
    """Truncates payment_transactions in demo_payment_db."""
    db_url = os.getenv(
        "DEMO_PAYMENT_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/demo_payment_db",
    )
    logger.info(f"Resetting demo payment database: {db_url}")

    try:
        import asyncpg

        conn = await asyncpg.connect(db_url, timeout=2.0)
        await conn.execute("TRUNCATE TABLE payment_transactions RESTART IDENTITY CASCADE;")
        await conn.close()
        logger.info("✓ Successfully truncated payment_transactions in demo_payment_db.")
        return True
    except Exception as e:
        logger.info(f"Live PostgreSQL demo_payment_db unavailable ({e}); clean in-memory state will initialize.")
        return False


async def reset_test_incidents():
    """Removes test incidents from aegisops_db."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/aegisops_db",
    )
    try:
        import asyncpg

        conn = await asyncpg.connect(db_url, timeout=2.0)
        await conn.execute("DELETE FROM action_proposals WHERE incident_id LIKE 'INC-DEMO-%' OR incident_id LIKE 'INC-BENCH-%' OR incident_id LIKE 'INC-TEST-%';")
        await conn.execute("DELETE FROM evidence WHERE incident_id LIKE 'INC-DEMO-%' OR incident_id LIKE 'INC-BENCH-%' OR incident_id LIKE 'INC-TEST-%';")
        await conn.execute("DELETE FROM incidents WHERE id LIKE 'INC-DEMO-%' OR id LIKE 'INC-BENCH-%' OR id LIKE 'INC-TEST-%';")
        await conn.close()
        logger.info("✓ Cleaned test incidents from aegisops_db.")
        return True
    except Exception:
        logger.info("aegisops_db not currently running; skipping database incident purge.")
        return False


async def reset_payment_simulator():
    """Calls /simulate/reset on payment-service simulator if running."""
    service_url = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8001")
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.post(f"{service_url}/simulate/reset")
            if res.status_code == 200:
                logger.info("✓ Reset payment-service simulator to nominal v2.8.0 baseline via HTTP.")
                return True
    except Exception:
        pass
    return False


async def reset_demo_async():
    logger.info("--- Starting AegisOps Demo Reset ---")
    await reset_demo_database()
    await reset_test_incidents()
    await reset_payment_simulator()
    logger.info("--- Demo Reset Complete ---")


def reset_demo():
    asyncio.run(reset_demo_async())


if __name__ == "__main__":
    reset_demo()
