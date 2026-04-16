"""
WhatsApp Cloud API integration - webhook handling, signature verification, and message sending.
"""
import hashlib
import hmac
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v21.0"


async def send_message(phone: str, text: str):
    """Send a WhatsApp text message."""
    url = f"{GRAPH_API}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                logger.info(f"Message sent to {phone}")
            else:
                logger.error(f"WhatsApp send error: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")


def verify_signature(body: bytes, signature: str) -> bool:
    """Verify Meta webhook signature (X-Hub-Signature-256)."""
    if not settings.whatsapp_app_secret:
        return True  # Skip in dev
    expected = "sha256=" + hmac.new(
        settings.whatsapp_app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_incoming(body: dict) -> tuple[str, str] | None:
    """Parse incoming WhatsApp webhook body. Returns (phone, message_text) or None."""
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "statuses" in entry:
            return None  # Status update, not a message
        if "contacts" not in entry:
            return None
        phone = entry["contacts"][0]["wa_id"]
        msg = entry["messages"][0]
        if msg["type"] == "text":
            return phone, msg["text"]["body"]
        elif msg["type"] == "interactive":
            if "button_reply" in msg.get("interactive", {}):
                return phone, msg["interactive"]["button_reply"]["title"]
            return phone, "[Interaccion no soportada]"
        return None
    except (KeyError, IndexError):
        return None
