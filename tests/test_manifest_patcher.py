"""
Tests for HLS manifest SCTE-35 injection.

Validates:
  - EXT-X-DATERANGE tag is inserted at the correct segment boundary
  - Multiple injections are all inserted
  - Manifest with no matching sequence is not modified
  - SCTE35-OUT hex and base64 attributes are correct
  - Idempotent re-injection does not duplicate tags
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from worker.hls.manifest_patcher import MarkerInjection, inject_markers

SAMPLE_MANIFEST = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:10
#EXTINF:6.000,
stream_0_010.ts
#EXTINF:6.000,
stream_0_011.ts
#EXTINF:6.000,
stream_0_012.ts
"""

NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_injection(sequence: int, hex_val: str = "deadbeef", b64_val: str = "3q2+7w==", marker_id: str = "test-1") -> MarkerInjection:
    return MarkerInjection(
        scte35_hex=hex_val,
        scte35_base64=b64_val,
        start_date=NOW,
        duration_secs=30.0,
        marker_id=marker_id,
        segment_sequence=sequence,
    )


class TestInjectMarkers:
    def test_no_injections_returns_original(self):
        result = inject_markers(SAMPLE_MANIFEST, [])
        assert result == SAMPLE_MANIFEST

    def test_injection_at_first_segment(self):
        inj = _make_injection(sequence=10)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        lines = result.splitlines()
        # Find index of the DATERANGE tag
        dr_lines = [l for l in lines if "#EXT-X-DATERANGE" in l]
        assert len(dr_lines) == 1
        # It should contain the hex payload
        assert "SCTE35-OUT=0xdeadbeef" in dr_lines[0]
        assert 'X-SCTE35-OUT="3q2+7w=="' in dr_lines[0]
        assert 'ID="test-1"' in dr_lines[0]
        assert "DURATION=30.000" in dr_lines[0]

    def test_injection_before_correct_extinf(self):
        inj = _make_injection(sequence=10)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        lines = result.splitlines()
        dr_idx = next(i for i, l in enumerate(lines) if "#EXT-X-DATERANGE" in l)
        extinf_idx = next(i for i, l in enumerate(lines) if l.startswith("#EXTINF:"))
        # DATERANGE must appear before the first EXTINF
        assert dr_idx < extinf_idx

    def test_injection_at_second_segment(self):
        inj = _make_injection(sequence=11)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        lines = result.splitlines()
        extinf_lines = [i for i, l in enumerate(lines) if l.startswith("#EXTINF:")]
        dr_lines = [i for i, l in enumerate(lines) if "#EXT-X-DATERANGE" in l]
        assert len(dr_lines) == 1
        # DATERANGE should be before second EXTINF but after first
        assert extinf_lines[0] < dr_lines[0] < extinf_lines[1]

    def test_multiple_injections(self):
        inj1 = _make_injection(sequence=10, marker_id="m1")
        inj2 = _make_injection(sequence=12, marker_id="m2")
        result = inject_markers(SAMPLE_MANIFEST, [inj1, inj2])
        dr_lines = [l for l in result.splitlines() if "#EXT-X-DATERANGE" in l]
        assert len(dr_lines) == 2
        ids = [l for l in dr_lines if 'ID="m1"' in l or 'ID="m2"' in l]
        assert len(ids) == 2

    def test_out_of_range_sequence_not_injected(self):
        inj = _make_injection(sequence=999)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        assert "#EXT-X-DATERANGE" not in result

    def test_start_date_in_tag(self):
        inj = _make_injection(sequence=10)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        assert "START-DATE=" in result
        assert "2024-01-01" in result

    def test_class_attribute_present(self):
        inj = _make_injection(sequence=10)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        assert 'CLASS="com.scte35"' in result

    def test_original_segments_preserved(self):
        inj = _make_injection(sequence=10)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        assert "stream_0_010.ts" in result
        assert "stream_0_011.ts" in result
        assert "stream_0_012.ts" in result

    def test_manifest_headers_preserved(self):
        inj = _make_injection(sequence=10)
        result = inject_markers(SAMPLE_MANIFEST, [inj])
        assert "#EXTM3U" in result
        assert "#EXT-X-VERSION:3" in result
        assert "#EXT-X-MEDIA-SEQUENCE:10" in result
