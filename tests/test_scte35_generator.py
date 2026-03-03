"""
Tests for SCTE-35 payload generation.

Validates:
  - CRC-32 correctness
  - Table ID and section header fields
  - splice_insert command encoding
  - time_signal command encoding
  - hex/base64 encoding outputs
  - SCTE35Payload dataclass helpers
"""

import base64
import struct
import sys
import os

# Make worker package importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

from worker.scte35.generator import (
    SCTE35Payload,
    SpliceCommandType,
    _calc_crc32_mpeg,
    build_splice_insert,
    build_time_signal,
)


def _verify_crc(data: bytes) -> bool:
    """Return True if the last 4 bytes are valid MPEG-2 CRC-32 over the preceding bytes."""
    payload = data[:-4]
    expected = struct.unpack(">I", data[-4:])[0]
    return _calc_crc32_mpeg(payload) == expected


class TestCRC32:
    def test_crc_known_value(self):
        """CRC result must be a 32-bit unsigned integer."""
        result = _calc_crc32_mpeg(b"")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_crc_deterministic(self):
        data = b"\x01\x02\x03\x04"
        assert _calc_crc32_mpeg(data) == _calc_crc32_mpeg(data)

    def test_crc_different_for_different_input(self):
        assert _calc_crc32_mpeg(b"\x01") != _calc_crc32_mpeg(b"\x02")


class TestSpliceInsert:
    def test_table_id(self):
        payload = build_splice_insert(splice_event_id=1)
        assert payload[0] == 0xFC, "table_id must be 0xFC"

    def test_crc_valid(self):
        payload = build_splice_insert(splice_event_id=42)
        assert _verify_crc(payload), "CRC-32 must be valid"

    def test_crc_valid_with_pts(self):
        payload = build_splice_insert(splice_event_id=1, pts_time=100.0, duration_secs=30.0)
        assert _verify_crc(payload)

    def test_crc_valid_immediate(self):
        payload = build_splice_insert(splice_event_id=5, pts_time=None)
        assert _verify_crc(payload)

    def test_command_type_byte(self):
        payload = build_splice_insert(splice_event_id=1)
        # The splice_command_type byte follows the tier+length bytes
        # Find it by scanning for 0x05 after the header
        # Header is 3 bytes (table_id + 2 section_length bytes)
        # Then: protocol_version(1) + encrypted(1) + pts_adj(4) + cw_index(1) + tier+len(3) = 10 bytes
        # splice_command_type is at offset 3+10 = 13
        assert payload[13] == SpliceCommandType.SPLICE_INSERT

    def test_splice_event_id_encoded(self):
        event_id = 0xDEADBEEF
        payload = build_splice_insert(splice_event_id=event_id)
        # splice_insert command starts at offset 14
        encoded_id = struct.unpack(">I", payload[14:18])[0]
        assert encoded_id == event_id & 0xFFFFFFFF

    def test_output_is_bytes(self):
        result = build_splice_insert(splice_event_id=1)
        assert isinstance(result, bytes)

    def test_minimum_length(self):
        # A minimal splice_insert section should be at least 20 bytes
        result = build_splice_insert(splice_event_id=1)
        assert len(result) >= 20

    def test_different_event_ids_produce_different_payloads(self):
        p1 = build_splice_insert(splice_event_id=1)
        p2 = build_splice_insert(splice_event_id=2)
        assert p1 != p2


class TestTimeSignal:
    def test_table_id(self):
        payload = build_time_signal(splice_event_id=1, pts_time=50.0)
        assert payload[0] == 0xFC

    def test_crc_valid(self):
        payload = build_time_signal(splice_event_id=1, pts_time=100.0)
        assert _verify_crc(payload)

    def test_command_type_byte(self):
        payload = build_time_signal(splice_event_id=1, pts_time=50.0)
        assert payload[13] == SpliceCommandType.TIME_SIGNAL

    def test_output_is_bytes(self):
        result = build_time_signal(splice_event_id=1, pts_time=0.0)
        assert isinstance(result, bytes)


class TestSCTE35Payload:
    def test_splice_insert_payload(self):
        p = SCTE35Payload.from_splice_insert(splice_event_id=1, pts_time=10.0, duration_secs=30.0)
        assert p.splice_type == "splice_insert"
        assert isinstance(p.binary, bytes)
        assert len(p.hex) == len(p.binary) * 2
        assert p.hex == p.binary.hex()
        assert p.base64 == base64.b64encode(p.binary).decode()
        assert p.pts_time == 10.0
        assert p.splice_event_id == 1

    def test_time_signal_payload(self):
        p = SCTE35Payload.from_time_signal(splice_event_id=2, pts_time=20.0)
        assert p.splice_type == "time_signal"
        assert isinstance(p.binary, bytes)
        assert p.base64 == base64.b64encode(p.binary).decode()

    def test_base64_is_valid(self):
        p = SCTE35Payload.from_splice_insert(splice_event_id=99)
        decoded = base64.b64decode(p.base64)
        assert decoded == p.binary

    def test_crc_valid_in_payload(self):
        p = SCTE35Payload.from_splice_insert(splice_event_id=7, pts_time=300.0, duration_secs=60.0)
        assert _verify_crc(p.binary)
