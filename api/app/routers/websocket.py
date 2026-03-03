import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.redis_service import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{channel_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: uuid.UUID):
    await websocket.accept()
    redis = await get_redis()
    pubsub = redis.pubsub()
    redis_channel = f"channel:{channel_id}"
    await pubsub.subscribe(redis_channel)
    logger.info("WebSocket client connected for channel %s", channel_id)
    try:
        while True:
            message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0)
            if message and message.get("type") == "message":
                await websocket.send_text(message["data"])
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info("WebSocket client disconnected for channel %s", channel_id)
    finally:
        await pubsub.unsubscribe(redis_channel)
        await pubsub.aclose()
