import aiosqlite
import json
from typing import Optional
from app.config import settings

DB_PATH = settings.database_url.replace("sqlite+aiosqlite:///", "")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL UNIQUE,
            gtc_url TEXT NOT NULL,
            company TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_routes_phone ON routes(phone);
        CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone, created_at);
    """)
    await db.commit()
    await db.close()


# ── Routes CRUD ──────────────────────────────────────

async def list_routes() -> list[dict]:
    db = await get_db()
    cursor = await db.execute_fetchall("SELECT * FROM routes ORDER BY phone")
    await db.close()
    return [dict(r) for r in cursor]


async def get_route_by_phone(phone: str) -> Optional[dict]:
    db = await get_db()
    cursor = await db.execute_fetchall(
        "SELECT * FROM routes WHERE phone = ? AND active = 1", (phone,)
    )
    await db.close()
    rows = [dict(r) for r in cursor]
    return rows[0] if rows else None


async def create_route(phone: str, gtc_url: str, company: str, username: str, password: str) -> dict:
    db = await get_db()
    await db.execute(
        "INSERT INTO routes (phone, gtc_url, company, username, password) VALUES (?, ?, ?, ?, ?)",
        (phone, gtc_url, company, username, password),
    )
    await db.commit()
    row = await db.execute_fetchall("SELECT * FROM routes WHERE phone = ?", (phone,))
    await db.close()
    return dict(row[0])


async def update_route(route_id: int, **kwargs) -> Optional[dict]:
    db = await get_db()
    sets = ", ".join(f"{k} = ?" for k in kwargs if k in ("phone", "gtc_url", "company", "username", "password", "active"))
    vals = [kwargs[k] for k in kwargs if k in ("phone", "gtc_url", "company", "username", "password", "active")]
    if not sets:
        await db.close()
        return None
    vals.append(route_id)
    await db.execute(f"UPDATE routes SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", vals)
    await db.commit()
    row = await db.execute_fetchall("SELECT * FROM routes WHERE id = ?", (route_id,))
    await db.close()
    return dict(row[0]) if row else None


async def delete_route(route_id: int) -> bool:
    db = await get_db()
    await db.execute("DELETE FROM routes WHERE id = ?", (route_id,))
    affected = db.total_changes
    await db.commit()
    await db.close()
    return affected > 0


# ── Conversations ────────────────────────────────────

async def save_message(phone: str, role: str, content: str):
    db = await get_db()
    await db.execute(
        "INSERT INTO conversations (phone, role, content) VALUES (?, ?, ?)",
        (phone, role, content),
    )
    await db.commit()
    await db.close()


async def get_conversation(phone: str, limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = await db.execute_fetchall(
        "SELECT role, content FROM conversations WHERE phone = ? ORDER BY created_at DESC LIMIT ?",
        (phone, limit),
    )
    await db.close()
    return [dict(r) for r in reversed(cursor)]


async def clear_conversation(phone: str):
    db = await get_db()
    await db.execute("DELETE FROM conversations WHERE phone = ?", (phone,))
    await db.commit()
    await db.close()
