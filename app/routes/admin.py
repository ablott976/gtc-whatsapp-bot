"""GoTimeCloud WhatsApp Bot - Admin API routes."""
import logging
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from app.config import settings
from app.database import (
    list_routes, create_route, update_route, delete_route,
    get_pool, fetch, fetchval,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api")


# ── Auth ──

class LoginRequest(BaseModel):
    username: str
    password: str


def create_token() -> str:
    payload = {
        "sub": settings.admin_user,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")


def verify_token(authorization: str) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        return False
    try:
        jwt.decode(authorization[7:], settings.admin_jwt_secret, algorithms=["HS256"])
        return True
    except jwt.InvalidTokenError:
        return False


async def require_auth(authorization: str = None):
    if not authorization or not verify_token(authorization):
        raise HTTPException(401, "Unauthorized")
    return True


@router.post("/login")
async def admin_login(req: LoginRequest):
    if req.username != settings.admin_user:
        raise HTTPException(401, "Invalid credentials")
    if req.password != settings.admin_password:
        raise HTTPException(401, "Invalid credentials")
    return {"token": create_token()}


# ── Routes CRUD ──

class RouteCreate(BaseModel):
    phone: str
    gtc_url: str
    company: str
    username: str
    password: str
    company_name: str = ""
    gtc_utc: int = 2
    language: str = "es"


class RouteUpdate(BaseModel):
    phone: str | None = None
    company_name: str | None = None
    gtc_url: str | None = None
    company: str | None = None
    username: str | None = None
    password: str | None = None
    gtc_utc: int | None = None
    language: str | None = None
    active: bool | None = None


@router.get("/routes")
async def admin_list_routes(_: bool = Depends(require_auth)):
    routes = await list_routes()
    for r in routes:
        if "password" in r:
            r["password"] = "****"
    return routes


@router.post("/routes")
async def admin_create_route(route: RouteCreate, _: bool = Depends(require_auth)):
    return await create_route(
        phone=route.phone,
        gtc_url=route.gtc_url,
        company=route.company,
        username=route.username,
        password=route.password,
        company_name=route.company_name,
        gtc_utc=route.gtc_utc,
        language=route.language,
    )


@router.put("/routes/{route_id}")
async def admin_update_route(route_id: int, route: RouteUpdate, _: bool = Depends(require_auth)):
    updates = {k: v for k, v in route.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await update_route(route_id, **updates)
    if not result:
        raise HTTPException(404, "Route not found")
    return result


@router.delete("/routes/{route_id}")
async def admin_delete_route(route_id: int, _: bool = Depends(require_auth)):
    if not await delete_route(route_id):
        raise HTTPException(404, "Route not found")
    return {"ok": True}


# ── Dashboard Stats ──

@router.get("/stats")
async def admin_stats(_: bool = Depends(require_auth)):
    pool = await get_pool()
    total_routes = await pool.fetchval("SELECT COUNT(*) FROM routes")
    active_routes = await pool.fetchval("SELECT COUNT(*) FROM routes WHERE active = true")
    messages_today = await pool.fetchval(
        "SELECT COUNT(*) FROM conversations WHERE created_at >= CURRENT_DATE"
    )
    return {
        "total_routes": total_routes,
        "active_routes": active_routes,
        "messages_today": messages_today,
    }


@router.get("/messages")
async def admin_messages(phone: str = None, limit: int = 50, _: bool = Depends(require_auth)):
    if phone:
        return await fetch(
            """SELECT * FROM conversations WHERE phone = $1
               ORDER BY created_at DESC LIMIT $2""", phone, limit)
    return await fetch(
        "SELECT * FROM conversations ORDER BY created_at DESC LIMIT $1", limit)
