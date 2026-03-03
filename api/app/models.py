import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    input_protocol: Mapped[str] = mapped_column(String(50), nullable=False, default="file")
    input_url: Mapped[str] = mapped_column(Text, nullable=False)
    output_dir: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="stopped")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    detection_events: Mapped[list["DetectionEvent"]] = relationship(back_populates="channel")
    scte_markers: Mapped[list["SCTEMarker"]] = relationship(back_populates="channel")


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    pts: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)

    channel: Mapped["Channel"] = relationship(back_populates="detection_events")


class SCTEMarker(Base):
    __tablename__ = "scte_markers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    pts: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    splice_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hex: Mapped[str] = mapped_column(Text, nullable=False)
    payload_base64: Mapped[str] = mapped_column(Text, nullable=False)
    segment_sequence: Mapped[int] = mapped_column(Integer, nullable=True)

    channel: Mapped["Channel"] = relationship(back_populates="scte_markers")
