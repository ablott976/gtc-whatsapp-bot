"""Database layer - PostgreSQL via asyncpg."""
import logging
from typing import Optional

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def init_db():
    """Run init.sql on startup."""
    pool = await get_pool()
    with open("sql/init.sql", "r") as f:
        await pool.execute(f.read())
    logger.info("Database initialized (PostgreSQL)")


# ── Query helpers ──────────────────────────────────────

async def fetchrow(query, *args):
    pool = await get_pool()
    row = await pool.fetchrow(query, *args)
    return dict(row) if row else None


async def fetch(query, *args):
    pool = await get_pool()
    return [dict(r) for r in await pool.fetch(query, *args)]


async def fetchval(query, *args):
    pool = await get_pool()
    return await pool.fetchval(query, *args)


async def execute(query, *args):
    pool = await get_pool()
    return await pool.execute(query, *args)


# ── Routes CRUD ─────────────────────────────────────────

async def list_routes() -> list[dict]:
    return await fetch("SELECT * FROM routes ORDER BY created_at DESC")


async def get_route_by_phone(phone: str) -> Optional[dict]:
    return await fetchrow("SELECT * FROM routes WHERE phone = $1 AND active = true", phone)


async def create_route(phone: str, gtc_url: str, company: str, username: str, password: str,
                       company_name: str = "", gtc_utc: int = 2, language: str = "es") -> dict:
    return await fetchrow(
        """INSERT INTO routes (phone, company_name, gtc_url, company, username, password, gtc_utc, language)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
        phone, company_name, gtc_url, company, username, password, gtc_utc, language,
    )


async def update_route(route_id: int, **kwargs) -> Optional[dict]:
    allowed = {"phone", "company_name", "gtc_url", "company", "username", "password", "gtc_utc", "language", "active"}
    filtered = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not filtered:
        return None
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(filtered.keys()))
    values = list(filtered.values())
    return await fetchrow(f"UPDATE routes SET {sets}, updated_at = NOW() WHERE id = $1 RETURNING *", route_id, *values)


async def delete_route(route_id: int) -> bool:
    result = await execute("DELETE FROM routes WHERE id = $1", route_id)
    return "DELETE" in str(result)


# ── Conversations ───────────────────────────────────────

async def save_message(phone: str, direction: str, content: str,
                       intent: str = None, route_id: int = None):
    await execute(
        """INSERT INTO conversations (route_id, phone, direction, message, intent)
           VALUES ($1, $2, $3, $4, $5)""",
        route_id, phone, direction, content[:4000], intent,
    )


async def get_conversation(phone: str, limit: int = 20) -> list[dict]:
    """Get conversation as [{role: 'user'|'model', content: '...'}] for Gemini."""
    rows = await fetch(
        "SELECT direction, message FROM conversations WHERE phone = $1 ORDER BY created_at DESC LIMIT $2",
        phone, limit,
    )
    result = []
    for r in reversed(rows):
        role = "user" if r["direction"] == "inbound" else "model"
        result.append({"role": role, "content": r["message"]})
    return result
