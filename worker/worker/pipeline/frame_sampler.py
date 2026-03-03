"""
Frame sampler: extracts frames from a video file/stream at a given FPS
using FFmpeg, feeding them to a detector.

Uses FFmpeg's image2pipe output to stream raw RGB frames.
"""

import logging
import subprocess
import threading
from pathlib import Path
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


class FrameSampler:
    """
    Extracts frames at sample_fps and calls frame_callback(frame_rgb, pts).
    Runs in a background thread.
    """

    def __init__(
        self,
        input_url: str,
        sample_fps: float,
        frame_callback: Callable[[np.ndarray, float], None],
        width: int = 320,
        height: int = 180,
    ) -> None:
        self._input_url = input_url
        self._sample_fps = sample_fps
        self._frame_callback = frame_callback
        self._width = width
        self._height = height
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "error",
            "-i", self._input_url,
            "-vf", f"fps={self._sample_fps},scale={self._width}:{self._height}",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-",
        ]
        frame_size = self._width * self._height * 3
        pts = 0.0
        pts_increment = 1.0 / self._sample_fps
        proc = None

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            while not self._stop_event.is_set():
                raw = proc.stdout.read(frame_size)
                if len(raw) < frame_size:
                    break
                frame = np.frombuffer(raw, dtype=np.uint8).reshape((self._height, self._width, 3))
                self._frame_callback(frame, pts)
                pts += pts_increment
        except Exception as exc:
            logger.error("Frame sampler error: %s", exc)
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
