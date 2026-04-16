"""Redis message batcher - groups rapid-fire messages from same phone."""
import asyncio
import json
import logging

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def queue_message(phone: str, text: str):
    """Queue a message for batching. Multiple messages from same phone
    are grouped together within the batch window."""
    r = await get_redis()
    key = f"gtc:batch:{phone}"

    # Add message to batch
    await r.rpush(key, json.dumps({"text": text}))
    await r.expire(key, 30)

    # Check if we already have a pending processor
    lock_key = f"gtc:lock:{phone}"
    locked = await r.set(lock_key, "1", nx=True, px=settings.batch_wait_ms + 2000)

    if locked:
        # We're the first message in this batch - schedule processing
        asyncio.create_task(_process_batch(phone))


async def _process_batch(phone: str):
    """Wait for batch window, then process all queued messages."""
    await asyncio.sleep(settings.batch_wait_ms / 1000)

    r = await get_redis()
    key = f"gtc:batch:{phone}"
    lock_key = f"gtc:lock:{phone}"

    # Get all messages
    messages = await r.lrange(key, 0, -1)
    await r.delete(key, lock_key)

    if not messages:
        return

    # Combine messages
    combined = " ".join(json.loads(m)["text"] for m in messages)

    # Import here to avoid circular imports
    from app.database import get_route_by_phone, save_message
    from app.whatsapp import send_message
    from app.ai_engine import process_message
    from app.gtc_client import GTCClient

    # Find route for this phone
    route = await get_route_by_phone(phone)
    if not route:
        await send_message(phone,
                           "Hola! Tu numero no esta configurado en el sistema. "
                           "Contacta con tu administrador para configurar el acceso.")
        return

    # Log inbound
    await save_message(phone, "inbound", combined, route_id=route.get("id"))

    try:
        # Create GTC client
        gtc = GTCClient(
            base_url=route["gtc_url"],
            company=route["company"],
            username=route["username"],
            password=route["password"],
            utc=route.get("gtc_utc", 2),
        )
        await gtc.connect()

        # Get conversation history
        from app.database import get_conversation
        history = await get_conversation(phone, limit=10)

        # Process through Gemini + GTC
        reply = await process_message(gtc, combined, history)

        # Log outbound
        await save_message(phone, "outbound", reply, route_id=route.get("id"))

        # Send reply
        await send_message(phone, reply)

    except Exception as e:
        logger.error(f"Batch processing error for {phone}: {e}")
        error_msg = "Error procesando tu mensaje. Intenta de nuevo en unos minutos."
        await send_message(phone, error_msg)
