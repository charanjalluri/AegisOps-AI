"""
Payment Service Database Interface
Handles real PostgreSQL connections to demo_payment_db with automatic in-memory fallback for offline testing.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger("payment_db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS payment_transactions (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    latency_ms NUMERIC(8, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

class PaymentDatabase:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DEMO_PAYMENT_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/demo_payment_db")
        self._memory_store: List[Dict[str, Any]] = []
        self._is_live_pg = False
        self.active_connections = 2
        self.max_connections = 50

    async def initialize(self) -> bool:
        """Attempts connection to live PostgreSQL; activates in-memory store if unreachable."""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.db_url, timeout=1.5)
            await conn.execute(CREATE_TABLE_SQL)
            await conn.close()
            self._is_live_pg = True
            logger.info("Connected to live demo_payment_db PostgreSQL.")
            return True
        except Exception as e:
            logger.info(f"Live PostgreSQL unavailable ({e}); utilizing in-memory transaction repository.")
            self._is_live_pg = False
            return False

    async def record_transaction(self, account_id: str, amount: float, currency: str, latency_ms: float, status: str = "completed") -> Dict[str, Any]:
        tx_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        record = {
            "id": tx_id,
            "account_id": account_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "latency_ms": latency_ms,
            "created_at": created_at,
        }

        if self._is_live_pg:
            try:
                import asyncpg
                conn = await asyncpg.connect(self.db_url, timeout=2.0)
                await conn.execute(
                    """
                    INSERT INTO payment_transactions (id, account_id, amount, currency, status, latency_ms, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    tx_id, account_id, amount, currency, status, latency_ms, created_at
                )
                await conn.close()
            except Exception as e:
                logger.warning(f"Failed writing to live PostgreSQL: {e}; falling back to memory.")
                self._memory_store.append(record)
        else:
            self._memory_store.append(record)

        return record

    async def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        if self._is_live_pg:
            try:
                import asyncpg
                conn = await asyncpg.connect(self.db_url, timeout=2.0)
                rows = await conn.fetch(
                    "SELECT id, account_id, amount, currency, status, latency_ms, created_at FROM payment_transactions ORDER BY created_at DESC LIMIT $1",
                    limit
                )
                await conn.close()
                return [dict(r) for r in rows]
            except Exception as e:
                logger.warning(f"Failed querying live PostgreSQL: {e}")
        
        return list(reversed(self._memory_store[-limit:]))

    async def reset(self):
        """Cleans transaction records (for demo reset)."""
        self._memory_store.clear()
        if self._is_live_pg:
            try:
                import asyncpg
                conn = await asyncpg.connect(self.db_url, timeout=2.0)
                await conn.execute("TRUNCATE TABLE payment_transactions")
                await conn.close()
            except Exception as e:
                logger.warning(f"Failed truncating table: {e}")

db = PaymentDatabase()
