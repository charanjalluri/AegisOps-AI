#!/usr/bin/env python3
"""
AegisOps AI - Demo State Reset Script
Truncates demo transactions and resets test state without destroying Docker infrastructure.
"""

import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reset_demo")

async def reset_demo_database():
    db_url = os.getenv("DEMO_PAYMENT_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/demo_payment_db")
    logger.info(f"Resetting demo payment database: {db_url}")

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url, timeout=3.0)
        await conn.execute("TRUNCATE TABLE payment_transactions RESTART IDENTITY CASCADE;")
        await conn.close()
        logger.info("Successfully truncated payment_transactions in demo_payment_db.")
        return True
    except Exception as e:
        logger.warning(f"Live PostgreSQL not reachable ({e}). Demo database will initialize clean on next boot.")
        return False

def reset_demo():
    logger.info("--- Starting AegisOps Demo Reset ---")
    asyncio.run(reset_demo_database())
    logger.info("--- Demo Reset Complete ---")

if __name__ == "__main__":
    reset_demo()
