import uuid
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Channel
from ..schemas import ChannelCreate, ChannelUpdate
from .redis_service import publish

logger = logging.getLogger(__name__)

WORKER_CONTROL_CHANNEL = "worker:control"


async def create_channel(db: AsyncSession, data: ChannelCreate) -> Channel:
    channel = Channel(**data.model_dump())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


async def list_channels(db: AsyncSession) -> list[Channel]:
    result = await db.execute(select(Channel).order_by(Channel.created_at.desc()))
    return list(result.scalars().all())


async def get_channel(db: AsyncSession, channel_id: uuid.UUID) -> Optional[Channel]:
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    return result.scalar_one_or_none()


async def update_channel(db: AsyncSession, channel: Channel, data: ChannelUpdate) -> Channel:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(channel, field, value)
    await db.commit()
    await db.refresh(channel)
    return channel


async def delete_channel(db: AsyncSession, channel: Channel) -> None:
    await db.delete(channel)
    await db.commit()


async def start_channel(db: AsyncSession, channel: Channel) -> Channel:
    channel.status = "starting"
    await db.commit()
    await db.refresh(channel)
    await publish(WORKER_CONTROL_CHANNEL, {"action": "start", "channel_id": str(channel.id)})
    logger.info("Sent start command for channel %s", channel.id)
    return channel


async def stop_channel(db: AsyncSession, channel: Channel) -> Channel:
    channel.status = "stopping"
    await db.commit()
    await db.refresh(channel)
    await publish(WORKER_CONTROL_CHANNEL, {"action": "stop", "channel_id": str(channel.id)})
    logger.info("Sent stop command for channel %s", channel.id)
    return channel


async def restart_channel(db: AsyncSession, channel: Channel) -> Channel:
    channel.status = "restarting"
    await db.commit()
    await db.refresh(channel)
    await publish(WORKER_CONTROL_CHANNEL, {"action": "restart", "channel_id": str(channel.id)})
    logger.info("Sent restart command for channel %s", channel.id)
    return channel
