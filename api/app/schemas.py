import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ChannelCreate(BaseModel):
    name: str
    input_protocol: str = "file"
    input_url: str
    output_dir: Optional[str] = None


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    input_protocol: Optional[str] = None
    input_url: Optional[str] = None
    output_dir: Optional[str] = None


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    input_protocol: str
    input_url: str
    output_dir: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class DetectionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: uuid.UUID
    pts: float
    timestamp: datetime
    event_type: str
    confidence: Optional[float]
    metadata: Optional[dict[str, Any]]


class SCTEMarkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: uuid.UUID
    pts: float
    timestamp: datetime
    splice_type: str
    payload_hex: str
    payload_base64: str
    segment_sequence: Optional[int]
