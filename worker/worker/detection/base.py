"""
Base detector interface and a CPU-only baseline detector.

The baseline detector works without any ML model by detecting:
  - Black frames (mean pixel value below threshold)
  - Scene changes (absolute frame diff above threshold)

To integrate YOLOv8:
  1. Install ultralytics: pip install ultralytics
  2. Subclass BaseDetector, override detect_frame()
  3. Load YOLO model in __init__ and run inference in detect_frame()
  4. For GPU: set device="cuda:0" in YOLO() constructor

# GPU enablement notes:
# - Install torch with CUDA: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# - Set CUDA_VISIBLE_DEVICES env var
# - Pass device="cuda" to YOLO() model
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    event_type: str
    confidence: float
    pts: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseDetector(ABC):
    """Abstract base for frame detectors."""

    @abstractmethod
    def detect_frame(self, frame: np.ndarray, pts: float) -> list[DetectionResult]:
        """
        Analyze a frame and return detection results.

        Args:
            frame: RGB numpy array of shape (H, W, 3), dtype uint8.
            pts: Presentation timestamp in seconds.

        Returns:
            List of DetectionResult objects (may be empty).
        """
        ...

    def close(self) -> None:
        """Release any resources held by the detector."""
        pass


class BaselineDetector(BaseDetector):
    """
    Heuristic detector using black-frame and scene-change detection.
    Works without any ML model — suitable for CPU-only environments.
    """

    def __init__(
        self,
        black_threshold: float = 16.0,
        scene_change_threshold: float = 30.0,
    ) -> None:
        self._black_threshold = black_threshold
        self._scene_change_threshold = scene_change_threshold
        self._prev_frame: np.ndarray | None = None

    def detect_frame(self, frame: np.ndarray, pts: float) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        gray = frame.mean(axis=2)  # (H, W) grayscale approximation

        mean_val = float(gray.mean())
        if mean_val < self._black_threshold:
            confidence = max(0.0, 1.0 - mean_val / self._black_threshold)
            results.append(
                DetectionResult(
                    event_type="black_frame",
                    confidence=round(confidence, 4),
                    pts=pts,
                    metadata={"mean_pixel": round(mean_val, 2)},
                )
            )

        if self._prev_frame is not None:
            diff = np.abs(gray.astype(np.float32) - self._prev_frame.astype(np.float32))
            mean_diff = float(diff.mean())
            if mean_diff > self._scene_change_threshold:
                confidence = min(1.0, mean_diff / 255.0)
                results.append(
                    DetectionResult(
                        event_type="scene_change",
                        confidence=round(confidence, 4),
                        pts=pts,
                        metadata={"mean_diff": round(mean_diff, 2)},
                    )
                )

        self._prev_frame = gray
        return results


class YOLOv8DetectorStub(BaseDetector):
    """
    Stub for YOLOv8 integration. Replace this with real implementation.

    To integrate:
        from ultralytics import YOLO
        self.model = YOLO("yolov8n.pt")  # or a custom model
        # In detect_frame:
        results = self.model(frame, device="cpu")  # or "cuda"
    """

    def __init__(self, model_path: str | None = None, device: str = "cpu") -> None:
        self.model_path = model_path
        self.device = device
        logger.warning(
            "YOLOv8DetectorStub loaded — replace with real ultralytics YOLO implementation. "
            "Model path: %s, Device: %s",
            model_path,
            device,
        )

    def detect_frame(self, frame: np.ndarray, pts: float) -> list[DetectionResult]:
        # Stub: returns no detections
        return []
