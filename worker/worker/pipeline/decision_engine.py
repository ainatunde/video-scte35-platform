"""
Decision engine: translates detection events into splice opportunities.

Applies debouncing and cooldown to avoid excessive SCTE-35 markers.
"""

import logging
import time
from dataclasses import dataclass

from ..detection.base import DetectionResult

logger = logging.getLogger(__name__)


@dataclass
class SpliceOpportunity:
    pts: float
    trigger_event_type: str
    confidence: float
    duration_secs: float | None = None


class DecisionEngine:
    """
    Converts detection results into splice decisions.

    Rules:
    - Only scene_change and black_frame events trigger splice opportunities.
    - A cooldown period prevents back-to-back splices.
    - A minimum confidence threshold filters weak detections.
    """

    TRIGGER_EVENTS = {"scene_change", "black_frame"}

    def __init__(
        self,
        cooldown_secs: float = 30.0,
        min_confidence: float = 0.5,
        default_duration_secs: float = 30.0,
    ) -> None:
        self._cooldown_secs = cooldown_secs
        self._min_confidence = min_confidence
        self._default_duration_secs = default_duration_secs
        self._last_splice_time: float | None = None

    def evaluate(self, detections: list[DetectionResult]) -> list[SpliceOpportunity]:
        opportunities: list[SpliceOpportunity] = []
        for det in detections:
            if det.event_type not in self.TRIGGER_EVENTS:
                continue
            if det.confidence < self._min_confidence:
                continue
            now = time.monotonic()
            if self._last_splice_time is not None and (now - self._last_splice_time) < self._cooldown_secs:
                logger.debug("Skipping splice opportunity (cooldown active): pts=%.3f", det.pts)
                continue
            self._last_splice_time = now
            opportunities.append(
                SpliceOpportunity(
                    pts=det.pts,
                    trigger_event_type=det.event_type,
                    confidence=det.confidence,
                    duration_secs=self._default_duration_secs,
                )
            )
            logger.info("Splice opportunity at pts=%.3f (trigger=%s)", det.pts, det.event_type)
        return opportunities
