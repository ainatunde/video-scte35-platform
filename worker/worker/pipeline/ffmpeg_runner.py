"""
FFmpeg pipeline runner for ABR HLS encoding.

Supports input protocols: file, RTMP, SRT.
Outputs HLS with 360p/480p/720p/1080p renditions using H.264 + AAC.

GPU notes:
  To enable NVENC hardware encoding, change:
    "-c:v", "libx264"  ->  "-c:v", "h264_nvenc"
  and add appropriate NVENC tuning flags.
  Set CUDA_VISIBLE_DEVICES and ensure nvidia-docker is used.
"""

import logging
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

ABR_RENDITIONS = [
    {"height": 360, "bitrate": "600k", "maxrate": "642k", "bufsize": "1200k", "audio_bitrate": "96k"},
    {"height": 480, "bitrate": "1400k", "maxrate": "1498k", "bufsize": "2800k", "audio_bitrate": "128k"},
    {"height": 720, "bitrate": "2800k", "maxrate": "2996k", "bufsize": "5600k", "audio_bitrate": "128k"},
    {"height": 1080, "bitrate": "5000k", "maxrate": "5350k", "bufsize": "10000k", "audio_bitrate": "192k"},
]


@dataclass
class PipelineConfig:
    channel_id: str
    input_url: str
    output_dir: Path
    segment_duration: int = 6
    hls_list_size: int = 10
    sample_fps: float = 2.0


def build_ffmpeg_command(config: PipelineConfig) -> list[str]:
    """Build FFmpeg command for ABR HLS output."""
    out = config.output_dir
    out.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-re",  # realtime input rate
        "-i", config.input_url,
    ]

    # Filter complex for multi-resolution
    filter_parts = []
    for i, r in enumerate(ABR_RENDITIONS):
        filter_parts.append(f"[v{i}]")
    split = f"[0:v]split={len(ABR_RENDITIONS)}" + "".join(f"[v{i}]" for i in range(len(ABR_RENDITIONS)))
    scale_parts = []
    for i, r in enumerate(ABR_RENDITIONS):
        scale_parts.append(f"[v{i}]scale=-2:{r['height']}[v{i}out]")
    filter_complex = split + ";" + ";".join(scale_parts)
    cmd += ["-filter_complex", filter_complex]

    # Map each rendition
    for i, r in enumerate(ABR_RENDITIONS):
        cmd += [
            "-map", f"[v{i}out]",
            "-map", "0:a",
            f"-c:v:{i}", "libx264",
            f"-b:v:{i}", r["bitrate"],
            f"-maxrate:{i}", r["maxrate"],
            f"-bufsize:{i}", r["bufsize"],
            f"-c:a:{i}", "aac",
            f"-b:a:{i}", r["audio_bitrate"],
        ]

    # HLS output
    var_stream_map = " ".join(f"v:{i},a:{i}" for i in range(len(ABR_RENDITIONS)))
    cmd += [
        "-f", "hls",
        "-hls_time", str(config.segment_duration),
        "-hls_list_size", str(config.hls_list_size),
        "-hls_flags", "independent_segments+delete_segments",
        "-hls_segment_type", "mpegts",
        "-hls_segment_filename", str(out / "stream_%v_%03d.ts"),
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", var_stream_map,
        str(out / "stream_%v.m3u8"),
    ]

    return cmd


class FFmpegRunner:
    """Runs and monitors an FFmpeg ABR pipeline in a subprocess."""

    def __init__(self, config: PipelineConfig, on_exit: Callable[[int], None] | None = None) -> None:
        self._config = config
        self._on_exit = on_exit
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        cmd = build_ffmpeg_command(self._config)
        logger.info("Starting FFmpeg: %s", " ".join(cmd))
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            logger.info("Sending SIGTERM to FFmpeg (channel %s)", self._config.channel_id)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg did not exit cleanly; sending SIGKILL")
                self._proc.kill()

    def _monitor(self) -> None:
        if self._proc is None:
            return
        _, stderr = self._proc.communicate()
        rc = self._proc.returncode
        if rc != 0:
            logger.warning("FFmpeg exited with code %d: %s", rc, stderr.decode(errors="replace"))
        else:
            logger.info("FFmpeg exited cleanly (channel %s)", self._config.channel_id)
        if self._on_exit:
            self._on_exit(rc)

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
