"""
Per-channel pipeline orchestrator.
Coordinates FFmpeg encoding, frame sampling, detection, decision engine,
SCTE-35 generation, and HLS manifest patching.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import redis

from ..config import settings
from ..detection.base import BaselineDetector, DetectionResult
from ..hls.manifest_patcher import MarkerInjection, patch_manifest_file
from ..pipeline.decision_engine import DecisionEngine
from ..pipeline.ffmpeg_runner import FFmpegRunner, PipelineConfig
from ..pipeline.frame_sampler import FrameSampler
from ..scte35.generator import SCTE35Payload

logger = logging.getLogger(__name__)


@dataclass
class ChannelConfig:
    channel_id: str
    name: str
    input_protocol: str
    input_url: str
    output_dir: str | None = None


class ChannelRunner:
    """Runs the full pipeline for a single channel."""

    def __init__(self, config: ChannelConfig, redis_client: redis.Redis) -> None:
        self._config = config
        self._redis = redis_client
        self._output_dir = Path(config.output_dir or settings.output_base_dir) / config.channel_id
        self._detector = BaselineDetector()
        self._decision_engine = DecisionEngine(
            cooldown_secs=settings.scte35_cooldown_seconds,
            min_confidence=0.5,
        )
        self._ffmpeg: FFmpegRunner | None = None
        self._sampler: FrameSampler | None = None
        self._splice_event_counter = 0
        self._running = False

    def start(self) -> None:
        logger.info("Starting pipeline for channel %s", self._config.channel_id)
        self._running = True
        pipeline_config = PipelineConfig(
            channel_id=self._config.channel_id,
            input_url=self._config.input_url,
            output_dir=self._output_dir,
            sample_fps=settings.detection_sample_fps,
        )
        self._ffmpeg = FFmpegRunner(pipeline_config, on_exit=self._on_ffmpeg_exit)
        self._ffmpeg.start()

        self._sampler = FrameSampler(
            input_url=self._config.input_url,
            sample_fps=settings.detection_sample_fps,
            frame_callback=self._on_frame,
        )
        self._sampler.start()
        self._publish_status("running")

    def stop(self) -> None:
        logger.info("Stopping pipeline for channel %s", self._config.channel_id)
        self._running = False
        if self._sampler:
            self._sampler.stop()
        if self._ffmpeg:
            self._ffmpeg.stop()
        self._publish_status("stopped")

    def _on_ffmpeg_exit(self, rc: int) -> None:
        if self._running:
            logger.warning("FFmpeg exited unexpectedly (rc=%d) for channel %s", rc, self._config.channel_id)
            self._publish_status("error")

    def _on_frame(self, frame: np.ndarray, pts: float) -> None:
        detections = self._detector.detect_frame(frame, pts)
        for det in detections:
            self._handle_detection(det)

        opportunities = self._decision_engine.evaluate(detections)
        for opp in opportunities:
            self._handle_splice_opportunity(pts=opp.pts, duration_secs=opp.duration_secs,
                                             trigger=opp.trigger_event_type)

    def _handle_detection(self, det: DetectionResult) -> None:
        event = {
            "type": "detection",
            "channel_id": self._config.channel_id,
            "event_type": det.event_type,
            "confidence": det.confidence,
            "pts": det.pts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": det.metadata,
        }
        self._publish_event(event)
        logger.debug("Detection: %s at pts=%.3f", det.event_type, det.pts)

    def _handle_splice_opportunity(self, pts: float, duration_secs: float | None, trigger: str) -> None:
        self._splice_event_counter += 1
        event_id = self._splice_event_counter

        payload = SCTE35Payload.from_splice_insert(
            splice_event_id=event_id,
            pts_time=pts,
            duration_secs=duration_secs,
            out_of_network=True,
        )

        marker_event = {
            "type": "marker",
            "channel_id": self._config.channel_id,
            "splice_type": payload.splice_type,
            "pts": pts,
            "payload_hex": payload.hex,
            "payload_base64": payload.base64,
            "duration_secs": duration_secs,
            "trigger": trigger,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._publish_event(marker_event)
        logger.info("SCTE-35 splice_insert generated at pts=%.3f", pts)

        # Attempt to patch the HLS manifest
        self._inject_hls_marker(pts, payload, duration_secs)

    def _inject_hls_marker(self, pts: float, payload: SCTE35Payload, duration_secs: float | None) -> None:
        """Inject SCTE-35 EXT-X-DATERANGE tag into HLS child manifests."""
        for i in range(4):  # 4 renditions
            manifest_path = self._output_dir / f"stream_{i}.m3u8"
            if not manifest_path.exists():
                continue
            segment_seq = int(pts / 6)  # approximate, based on 6s segments
            injection = MarkerInjection(
                scte35_hex=payload.hex,
                scte35_base64=payload.base64,
                start_date=datetime.now(timezone.utc),
                duration_secs=duration_secs,
                marker_id=f"scte35-{payload.splice_event_id}",
                segment_sequence=segment_seq,
            )
            try:
                patch_manifest_file(manifest_path, [injection])
            except Exception as exc:
                logger.warning("Failed to patch manifest %s: %s", manifest_path, exc)

    def _publish_event(self, event: dict) -> None:
        channel_key = f"channel:{self._config.channel_id}"
        try:
            self._redis.publish(channel_key, json.dumps(event))
        except redis.RedisError as exc:
            logger.warning("Failed to publish event: %s", exc)

    def _publish_status(self, status: str) -> None:
        self._publish_event({
            "type": "status",
            "channel_id": self._config.channel_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
