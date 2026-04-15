"""
GoTimeCloud WhatsApp Chatbot - Main FastAPI Application
"""
import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt

from app.config import settings
from app.database import init_db, get_route_by_phone, save_message, get_conversation, list_routes, create_route, update_route, delete_route
from app.gtc_client import GTCClient
from app.ai_engine import process_message
from app.whatsapp import send_message, parse_incoming

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SECRET_KEY = settings.admin_password + "_jwt_secret"


def make_token() -> str:
    return jwt.encode({"admin": True, "exp": datetime.utcnow().timestamp() + 86400}, SECRET_KEY)


def verify_token(request: Request) -> bool:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            jwt.decode(auth[7:], SECRET_KEY)
            return True
        except:
            pass
    raise HTTPException(401, "Not authenticated")


# ── Clients cache ──────────────────────────────────────
_gtc_clients: dict[str, GTCClient] = {}


async def get_gtc_client(phone: str) -> GTCClient | None:
    route = await get_route_by_phone(phone)
    if not route:
        return None
    cache_key = f"{route['gtc_url']}_{route['company']}_{route['username']}"
    if cache_key in _gtc_clients:
        client = _gtc_clients[cache_key]
        client.token = None  # Force re-login
    else:
        client = GTCClient(route["gtc_url"], route["company"], route["username"], route["password"])
        _gtc_clients[cache_key] = client
    try:
        await client.connect()
        return client
    except Exception as e:
        logger.error(f"GTC connect failed for {phone}: {e}")
        return None


# ── Lifespan ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="GTC WhatsApp Bot", lifespan=lifespan)


# ── WhatsApp Webhook ───────────────────────────────────

@app.get("/webhook")
async def webhook_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified")
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(403, "Verification failed")


@app.post("/webhook")
async def webhook_receive(request: Request):
    body = await request.json()

    # Always return 200 quickly (Meta requirement)
    result = parse_incoming(body)
    if not result:
        return Response(status_code=200)

    phone, message_text = result
    logger.info(f"Message from {phone}: {message_text[:50]}")

    # Look up GTC client for this phone
    gtc = await get_gtc_client(phone)
    if not gtc:
        await send_message(phone, "Tu numero no esta configurado en el sistema. Contacta con tu administrador.")
        return Response(status_code=200)

    # Save user message
    await save_message(phone, "user", message_text)

    # Get conversation history
    history = await get_conversation(phone, limit=20)

    # Process through Gemini + GTC
    try:
        reply = await process_message(gtc, message_text, history)
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        reply = f"Error al procesar tu mensaje. Intenta de nuevo en unos segundos."

    # Save assistant reply
    await save_message(phone, "assistant", reply)

    # Send reply via WhatsApp
    await send_message(phone, reply)

    return Response(status_code=200)


# ── Health ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ── Test endpoint ──────────────────────────────────────

@app.get("/api/test/{phone}")
async def test_connection(phone: str):
    gtc = await get_gtc_client(phone)
    if not gtc:
        return {"status": "error", "message": "Numero no configurado"}
    try:
        sub = await gtc.get_subscription()
        return {"status": "ok", "subscription": sub}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Dashboard API ──────────────────────────────────────

@app.post("/admin/api/login")
async def admin_login(request: Request):
    data = await request.json()
    if data.get("password") == settings.admin_password:
        return {"token": make_token()}
    raise HTTPException(401, "Wrong password")


@app.get("/admin/api/routes")
async def admin_list_routes(_: bool = Depends(verify_token)):
    routes = await list_routes()
    # Mask passwords
    for r in routes:
        r["password"] = "****" if r.get("password") else ""
    return routes


@app.post("/admin/api/routes")
async def admin_create_route(request: Request, _: bool = Depends(verify_token)):
    data = await request.json()
    route = await create_route(
        phone=data["phone"],
        gtc_url=data["gtc_url"],
        company=data["company"],
        username=data["username"],
        password=data["password"],
    )
    return route


@app.put("/admin/api/routes/{route_id}")
async def admin_update_route(route_id: int, request: Request, _: bool = Depends(verify_token)):
    data = await request.json()
    route = await update_route(route_id, **data)
    if not route:
        raise HTTPException(404, "Route not found")
    return route


@app.delete("/admin/api/routes/{route_id}")
async def admin_delete_route(route_id: int, _: bool = Depends(verify_token)):
    ok = await delete_route(route_id)
    if not ok:
        raise HTTPException(404, "Route not found")
    return {"ok": True}


# ── Dashboard HTML ─────────────────────────────────────

@app.get("/admin")
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GTC Bot - Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
.login { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.login-box { background: #1e293b; padding: 2rem; border-radius: 12px; width: 100%; max-width: 360px; }
.login-box h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #38bdf8; }
.login-box p { font-size: 0.85rem; color: #94a3b8; margin-bottom: 1.5rem; }
input { width: 100%; padding: 0.75rem; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #e2e8f0; font-size: 1rem; margin-bottom: 1rem; }
button { width: 100%; padding: 0.75rem; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
button:hover { background: #1d4ed8; }
.dash { display: none; padding: 2rem; max-width: 900px; margin: 0 auto; }
.dash.active { display: block; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header h1 { color: #38bdf8; }
.btn { padding: 0.5rem 1rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.9rem; }
.btn-primary { background: #2563eb; color: white; }
.btn-danger { background: #dc2626; color: white; }
.btn-sm { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
th { background: #334155; padding: 0.75rem; text-align: left; font-size: 0.85rem; color: #94a3b8; }
td { padding: 0.75rem; border-top: 1px solid #334155; font-size: 0.9rem; }
.modal-bg { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); align-items: center; justify-content: center; }
.modal-bg.active { display: flex; }
.modal { background: #1e293b; padding: 2rem; border-radius: 12px; width: 100%; max-width: 480px; }
.modal h2 { margin-bottom: 1rem; color: #38bdf8; }
label { display: block; font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.25rem; margin-top: 0.75rem; }
.error { color: #f87171; font-size: 0.85rem; margin-top: 0.5rem; display: none; }
.actions { display: flex; gap: 0.5rem; }
</style>
</head>
<body>

<div class="login" id="loginView">
  <div class="login-box">
    <h1>GTC WhatsApp Bot</h1>
    <p>Dashboard de configuracion</p>
    <input type="password" id="loginPass" placeholder="Contrasena" onkeydown="if(event.key==='Enter')login()">
    <button onclick="login()">Entrar</button>
    <div class="error" id="loginError">Contrasena incorrecta</div>
  </div>
</div>

<div class="dash" id="dashView">
  <div class="header">
    <h1>Routing: Telefono a Empresa GTC</h1>
    <button class="btn btn-primary" onclick="openModal()">+ Nueva ruta</button>
  </div>
  <table>
    <thead>
      <tr><th>Telefono</th><th>URL GTC</th><th>Empresa</th><th>Usuario</th><th>Acciones</th></tr>
    </thead>
    <tbody id="routesTable"></tbody>
  </table>
</div>

<div class="modal-bg" id="modal">
  <div class="modal">
    <h2 id="modalTitle">Nueva ruta</h2>
    <input type="hidden" id="editId">
    <label>Telefono (con pais, sin +)</label>
    <input id="fPhone" placeholder="34600000000">
    <label>URL GoTimeCloud</label>
    <input id="fUrl" placeholder="https://demo.gotimecloud.com">
    <label>Nombre empresa</label>
    <input id="fCompany" placeholder="demo">
    <label>Usuario GTC</label>
    <input id="fUser" placeholder="admin">
    <label>Contrasena GTC</label>
    <input id="fPass" type="password" placeholder="1234">
    <div style="display:flex;gap:0.5rem;margin-top:1.5rem">
      <button onclick="saveRoute()">Guardar</button>
      <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
    </div>
    <div class="error" id="modalError"></div>
  </div>
</div>

<script>
let token = localStorage.getItem('gtc_token') || '';

async function api(method, path, body) {
  const opts = { method, headers: { 'Authorization': 'Bearer ' + token } };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const resp = await fetch('/admin/api' + path, opts);
  if (resp.status === 401) { localStorage.removeItem('gtc_token'); token = ''; showLogin(); throw new Error('auth'); }
  return resp.json();
}

function showLogin() { document.getElementById('loginView').style.display = 'flex'; document.getElementById('dashView').classList.remove('active'); }
function showDash() { document.getElementById('loginView').style.display = 'none'; document.getElementById('dashView').classList.add('active'); loadRoutes(); }

async function login() {
  const pass = document.getElementById('loginPass').value;
  try {
    const r = await fetch('/admin/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: pass }) });
    if (!r.ok) throw 0;
    const d = await r.json();
    token = d.token; localStorage.setItem('gtc_token', token);
    document.getElementById('loginError').style.display = 'none';
    showDash();
  } catch { document.getElementById('loginError').style.display = 'block'; }
}

async function loadRoutes() {
  try {
    const routes = await api('GET', '/routes');
    const tbody = document.getElementById('routesTable');
    tbody.innerHTML = routes.map(r => `<tr>
      <td>${r.phone}</td><td>${r.gtc_url}</td><td>${r.company}</td><td>${r.username}</td>
      <td class="actions">
        <button class="btn btn-sm btn-primary" onclick="editRoute(${r.id},'${r.phone}','${r.gtc_url}','${r.company}','${r.username}')">Editar</button>
        <button class="btn btn-sm btn-danger" onclick="delRoute(${r.id})">Eliminar</button>
      </td>
    </tr>`).join('');
  } catch {}
}

function openModal() {
  document.getElementById('editId').value = '';
  document.getElementById('modalTitle').textContent = 'Nueva ruta';
  ['fPhone','fUrl','fCompany','fUser','fPass'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('modal').classList.add('active');
}

function editRoute(id, phone, url, company, user) {
  document.getElementById('editId').value = id;
  document.getElementById('modalTitle').textContent = 'Editar ruta';
  document.getElementById('fPhone').value = phone;
  document.getElementById('fUrl').value = url;
  document.getElementById('fCompany').value = company;
  document.getElementById('fUser').value = user;
  document.getElementById('fPass').value = '';
  document.getElementById('modal').classList.add('active');
}

function closeModal() { document.getElementById('modal').classList.remove('active'); }

async function saveRoute() {
  const id = document.getElementById('editId').value;
  const data = {
    phone: document.getElementById('fPhone').value,
    gtc_url: document.getElementById('fUrl').value,
    company: document.getElementById('fCompany').value,
    username: document.getElementById('fUser').value,
    password: document.getElementById('fPass').value,
  };
  if (!data.phone || !data.gtc_url || !data.company || !data.username) {
    document.getElementById('modalError').textContent = 'Todos los campos excepto contrasena son obligatorios';
    document.getElementById('modalError').style.display = 'block'; return;
  }
  if (!id && !data.password) {
    document.getElementById('modalError').textContent = 'La contrasena es obligatoria para nuevas rutas';
    document.getElementById('modalError').style.display = 'block'; return;
  }
  try {
    if (id) { await api('PUT', '/routes/' + id, data); } else { await api('POST', '/routes', data); }
    closeModal(); loadRoutes();
  } catch (e) { document.getElementById('modalError').textContent = 'Error al guardar'; document.getElementById('modalError').style.display = 'block'; }
}

async function delRoute(id) {
  if (!confirm('Eliminar esta ruta?')) return;
  try { await api('DELETE', '/routes/' + id); loadRoutes(); } catch {}
}

// Auto-login if token exists
if (token) showDash();
</script>
</body>
</html>"""
