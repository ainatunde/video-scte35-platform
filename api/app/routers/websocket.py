import asyncio
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

    receive_task = asyncio.create_task(websocket.receive_text())
    try:
        while True:
            # timeout=1.0 lets redis-py yield control each second rather than
            # spinning in a tight loop when there are no messages.
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                await websocket.send_text(message["data"])

            if receive_task.done():
                # Re-raise any exception from the receive task (e.g. WebSocketDisconnect)
                receive_task.result()
                receive_task = asyncio.create_task(websocket.receive_text())
    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info("WebSocket client disconnected for channel %s", channel_id)
    finally:
        receive_task.cancel()
        await pubsub.unsubscribe(redis_channel)
        await pubsub.aclose()
