"""
HLS manifest patcher.

Injects EXT-X-DATERANGE tags containing SCTE-35 payloads into HLS playlists.
The EXT-X-DATERANGE tag is the standard way to carry SCTE-35 data in HLS per
RFC 8216 Section 4.4.5.1 and the SCTE-35 HLS signaling specification.

Tag format:
    #EXT-X-DATERANGE:ID="...",START-DATE="...",DURATION=30,
        SCTE35-OUT=0x<hex>,X-SCTE35-OUT="<base64>"
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex to find the segment line that follows a given sequence number
_EXTINF_RE = re.compile(r"^#EXTINF:(\d+(?:\.\d+)?),")
_SEQUENCE_RE = re.compile(r"^#EXT-X-MEDIA-SEQUENCE:(\d+)")


@dataclass
class MarkerInjection:
    """Describes a SCTE-35 marker to inject."""
    scte35_hex: str
    scte35_base64: str
    start_date: datetime
    duration_secs: float | None
    marker_id: str
    segment_sequence: int  # inject before this segment


def _build_daterange_tag(injection: MarkerInjection) -> str:
    """Build an EXT-X-DATERANGE tag line for a SCTE-35 marker."""
    start_str = injection.start_date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    parts = [
        f'ID="{injection.marker_id}"',
        f'CLASS="com.scte35"',
        f'START-DATE="{start_str}"',
    ]
    if injection.duration_secs is not None:
        parts.append(f"DURATION={injection.duration_secs:.3f}")
    parts.append(f"SCTE35-OUT=0x{injection.scte35_hex}")
    parts.append(f'X-SCTE35-OUT="{injection.scte35_base64}"')
    return "#EXT-X-DATERANGE:" + ",".join(parts)


def inject_markers(manifest_text: str, injections: list[MarkerInjection]) -> str:
    """
    Inject SCTE-35 EXT-X-DATERANGE tags into an HLS manifest.

    Tags are inserted immediately before the #EXTINF line of the target segment.

    Args:
        manifest_text: Original HLS manifest content.
        injections: List of markers to inject.

    Returns:
        Modified manifest text with SCTE-35 tags inserted.
    """
    if not injections:
        return manifest_text

    # Build a map of sequence -> list of injection tags
    injection_map: dict[int, list[str]] = {}
    for inj in injections:
        tag = _build_daterange_tag(inj)
        injection_map.setdefault(inj.segment_sequence, []).append(tag)

    lines = manifest_text.splitlines(keepends=True)
    output: list[str] = []
    current_sequence: int | None = None
    segment_index = 0

    for line in lines:
        stripped = line.rstrip("\n\r")

        seq_match = _SEQUENCE_RE.match(stripped)
        if seq_match:
            current_sequence = int(seq_match.group(1))
            output.append(line)
            continue

        if _EXTINF_RE.match(stripped):
            abs_seq = (current_sequence or 0) + segment_index
            if abs_seq in injection_map:
                for tag in injection_map[abs_seq]:
                    output.append(tag + "\n")
                    logger.debug("Injected SCTE-35 tag at sequence %d", abs_seq)
            segment_index += 1

        output.append(line)

    return "".join(output)


def patch_manifest_file(manifest_path: Path, injections: list[MarkerInjection]) -> None:
    """Read, patch, and write back an HLS manifest file."""
    original = manifest_path.read_text()
    patched = inject_markers(original, injections)
    manifest_path.write_text(patched)
    logger.info("Patched manifest %s with %d SCTE-35 markers", manifest_path, len(injections))
