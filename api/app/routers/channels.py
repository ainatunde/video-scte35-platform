import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import ChannelCreate, ChannelResponse, ChannelUpdate
from ..services import channel_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])


async def _get_or_404(channel_id: uuid.UUID, db: AsyncSession) -> object:
    channel = await channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return channel


@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(data: ChannelCreate, db: AsyncSession = Depends(get_db)):
    return await channel_service.create_channel(db, data)


@router.get("/", response_model=List[ChannelResponse])
async def list_channels(db: AsyncSession = Depends(get_db)):
    return await channel_service.list_channels(db)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_or_404(channel_id, db)


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(channel_id: uuid.UUID, data: ChannelUpdate, db: AsyncSession = Depends(get_db)):
    channel = await _get_or_404(channel_id, db)
    return await channel_service.update_channel(db, channel, data)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    channel = await _get_or_404(channel_id, db)
    await channel_service.delete_channel(db, channel)


@router.post("/{channel_id}/start", response_model=ChannelResponse)
async def start_channel(channel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    channel = await _get_or_404(channel_id, db)
    return await channel_service.start_channel(db, channel)


@router.post("/{channel_id}/stop", response_model=ChannelResponse)
async def stop_channel(channel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    channel = await _get_or_404(channel_id, db)
    return await channel_service.stop_channel(db, channel)


@router.post("/{channel_id}/restart", response_model=ChannelResponse)
async def restart_channel(channel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    channel = await _get_or_404(channel_id, db)
    return await channel_service.restart_channel(db, channel)
