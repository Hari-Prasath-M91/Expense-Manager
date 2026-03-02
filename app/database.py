# ============================================================================
# Database Connection Pool — asyncpg wrapper
# ============================================================================
from __future__ import annotations

import asyncpg
from app.config import settings


class DatabasePool:
    """Thin wrapper around asyncpg connection pool."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=settings.asyncpg_dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        # Auto-migration: Ensure necessary columns exist
        async with self._pool.acquire() as conn:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_refresh_token TEXT")
            await conn.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS gmail_msg_id VARCHAR(255) UNIQUE")

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()

    # --- convenience methods -------------------------------------------------

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
