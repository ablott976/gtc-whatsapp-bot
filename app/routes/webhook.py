"""GoTimeCloud WhatsApp Bot - Webhook routes."""
import logging

from fastapi import APIRouter, Request, Response

from app.config import settings
from app.whatsapp import verify_signature, parse_incoming
from app.batcher import queue_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhook")
async def webhook_verify(request: Request):
    """Meta webhook verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified")
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def webhook_receive(request: Request):
    """Receive WhatsApp messages."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Verify signature
    if not verify_signature(body, signature):
        return Response(content="Unauthorized", status_code=401)

    payload = await request.json()

    # Handle status updates (delivered, read, etc.) - just ACK
    result = parse_incoming(payload)
    if not result:
        return Response(status_code=200)

    phone, message_text = result
    logger.info(f"Message from {phone}: {message_text[:50]}")

    # Queue for batching
    await queue_message(phone, message_text)

    return Response(status_code=200)
