"""
WhatsApp Cloud API integration - webhook handling and message sending.
"""
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
        "text": {"body": text[:4096]},  # WhatsApp limit
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


def parse_incoming(body: dict) -> tuple[str, str] | None:
    """Parse incoming WhatsApp webhook body. Returns (phone, message_text) or None."""
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "contacts" not in entry:
            return None  # Status update, not a message
        phone = entry["contacts"][0]["wa_id"]
        msg = entry["messages"][0]
        if msg["type"] == "text":
            return phone, msg["text"]["body"]
        elif msg["type"] == "interactive":
            # Handle button responses
            if "button_reply" in msg.get("interactive", {}):
                return phone, msg["interactive"]["button_reply"]["title"]
            return phone, "[Interaccion no soportada]"
        return None
    except (KeyError, IndexError):
        return None
