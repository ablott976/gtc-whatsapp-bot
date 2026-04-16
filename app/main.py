"""
GoTimeCloud WhatsApp Bot - Main FastAPI Application
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routes.webhook import router as webhook_router
from app.routes.admin import router as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("GTC WhatsApp Bot started")
    yield


app = FastAPI(title="GTC WhatsApp Bot", version="3.0", lifespan=lifespan)

# Include API routers
app.include_router(webhook_router)
app.include_router(admin_router)


# ── Health ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0", "time": datetime.utcnow().isoformat()}


# ── Serve React SPA Admin Dashboard ────────────────────

ADMIN_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin", "dist")


@app.get("/admin")
async def serve_admin():
    index = os.path.join(ADMIN_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "Admin dashboard not built. Run: cd admin && npm install && npm run build"}


@app.get("/admin/{path:path}")
async def serve_admin_assets(path: str):
    file_path = os.path.join(ADMIN_DIST, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    # SPA fallback
    index = os.path.join(ADMIN_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "Admin dashboard not built"}


# Mount static assets for admin SPA
try:
    assets_dir = os.path.join(ADMIN_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/admin/assets", StaticFiles(directory=assets_dir), name="admin-assets")
except Exception:
    pass  # Assets don't exist yet during development
