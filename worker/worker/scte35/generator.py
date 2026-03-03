"""
SCTE-35 payload generator.

Implements splice_insert and time_signal command encoding per SCTE-35 2022.
Outputs binary, hex, and base64 representations.

Reference: SCTE-35 2022 Digital Program Insertion Cueing Message for Cable
"""

import base64
import struct
from dataclasses import dataclass
from enum import IntEnum


class SpliceCommandType(IntEnum):
    SPLICE_NULL = 0x00
    SPLICE_INSERT = 0x05
    TIME_SIGNAL = 0x06


def _calc_crc32_mpeg(data: bytes) -> int:
    """Calculate MPEG-2 CRC-32 as used by SCTE-35."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = (crc << 1) ^ 0x04C11DB7
            else:
                crc <<= 1
            crc &= 0xFFFFFFFF
    return crc


def _encode_splice_time(pts_time: float | None) -> bytes:
    """
    Encode a splice_time() structure.
    If pts_time is None, time_specified_flag = 0 (immediate).
    pts_time is in seconds; internally stored as 90kHz ticks.
    """
    if pts_time is None:
        # time_specified_flag = 0, reserved = 0x7F
        return bytes([0x7F])
    ticks = int(pts_time * 90000) & 0x1FFFFFFFF
    # [time_specified_flag(1)] [reserved(6)] [pts_time(33)] = 40 bits (5 bytes)
    val = (1 << 39) | (0x3F << 33) | (ticks & 0x1FFFFFFFF)
    return val.to_bytes(5, "big")


def _encode_break_duration(duration_secs: float, auto_return: bool = True) -> bytes:
    """Encode break_duration() - 6 bytes: auto_return(1) + reserved(6) + duration(33)."""
    ticks = int(duration_secs * 90000) & 0x1FFFFFFFF
    auto_bit = 1 if auto_return else 0
    val = (auto_bit << 39) | (0x3F << 33) | ticks
    return val.to_bytes(6, "big")


def build_splice_insert(
    splice_event_id: int,
    pts_time: float | None = None,
    duration_secs: float | None = None,
    out_of_network: bool = True,
    program_splice: bool = True,
    auto_return: bool = True,
) -> bytes:
    """
    Build a SCTE-35 SpliceInfoSection with splice_insert command.

    Args:
        splice_event_id: Unique 32-bit identifier for this splice event.
        pts_time: PTS time in seconds when splice should occur (None = immediate).
        duration_secs: Duration of the break in seconds (None = no duration).
        out_of_network: True for ad insertion (out-of-network indicator).
        program_splice: True for program-level splice.
        auto_return: If True, return to network automatically after duration.

    Returns:
        Complete SCTE-35 section bytes including CRC-32.
    """
    # Build splice_insert() command bytes
    cmd = bytearray()
    cmd += struct.pack(">I", splice_event_id & 0xFFFFFFFF)
    # splice_event_cancel_indicator=0, reserved=0x7F
    cmd.append(0x7F)

    # out_of_network_indicator(1) | program_splice_flag(1) | duration_flag(1) | splice_immediate_flag(1) | reserved(4)
    duration_flag = 1 if duration_secs is not None else 0
    splice_immediate_flag = 1 if pts_time is None else 0
    flags = (
        (1 if out_of_network else 0) << 7
        | (1 if program_splice else 0) << 6
        | duration_flag << 5
        | splice_immediate_flag << 4
        | 0x0F  # reserved bits set to 1
    )
    cmd.append(flags)

    if program_splice and not splice_immediate_flag:
        cmd += _encode_splice_time(pts_time)

    if duration_flag:
        cmd += _encode_break_duration(duration_secs, auto_return)

    # unique_program_id, avail_num, avails_expected
    cmd += struct.pack(">HBB", 0x0001, 0x00, 0x00)

    splice_command_length = len(cmd)

    # Build descriptor_loop (empty for MVP)
    descriptor_loop = b""
    descriptor_loop_length = len(descriptor_loop)

    # Build section body (before CRC)
    body = bytearray()
    body.append(0xFC)  # table_id
    # section_syntax_indicator(0) | private_indicator(0) | reserved(11) | section_length(12)
    # section_length covers from protocol_version to CRC32 (inclusive)
    # We'll patch this after computing full length
    body.append(0x00)  # placeholder MSB
    body.append(0x00)  # placeholder LSB
    body.append(0x00)  # protocol_version
    body.append(0x00)  # encrypted_packet(0) | encryption_algorithm(6) | pts_adjustment MSB
    body += struct.pack(">I", 0x00000000)  # pts_adjustment lower 32 bits (0)
    body.append(0x00)  # cw_index
    # tier(12) | splice_command_length(12)
    body.append(0xFF)  # tier MSB (0xFFF >> 4)
    body.append(0xF0 | ((splice_command_length >> 8) & 0x0F))  # tier LSB (4 bits) | cmd_len MSB
    body.append(splice_command_length & 0xFF)  # cmd_len LSB
    body.append(SpliceCommandType.SPLICE_INSERT)
    body += cmd
    body += struct.pack(">H", descriptor_loop_length)
    body += descriptor_loop

    # section_length = bytes from protocol_version to CRC32 = len(body) - 3 + 4
    section_length = len(body) - 3 + 4  # subtract 3-byte header, add 4-byte CRC
    body[1] = 0x70 | ((section_length >> 8) & 0x0F)
    body[2] = section_length & 0xFF

    crc = _calc_crc32_mpeg(bytes(body))
    body += struct.pack(">I", crc)
    return bytes(body)


def build_time_signal(
    splice_event_id: int,
    pts_time: float,
) -> bytes:
    """
    Build a SCTE-35 SpliceInfoSection with time_signal command.

    Args:
        splice_event_id: Used as part of segmentation descriptor (informational).
        pts_time: PTS time in seconds for the time signal.

    Returns:
        Complete SCTE-35 section bytes including CRC-32.
    """
    cmd = _encode_splice_time(pts_time)
    splice_command_length = len(cmd)

    descriptor_loop = b""
    descriptor_loop_length = 0

    body = bytearray()
    body.append(0xFC)
    body.append(0x00)
    body.append(0x00)
    body.append(0x00)  # protocol_version
    body.append(0x00)  # encrypted_packet + pts_adjustment MSB
    body += struct.pack(">I", 0x00000000)
    body.append(0x00)  # cw_index
    body.append(0xFF)
    body.append(0xF0 | ((splice_command_length >> 8) & 0x0F))
    body.append(splice_command_length & 0xFF)
    body.append(SpliceCommandType.TIME_SIGNAL)
    body += cmd
    body += struct.pack(">H", descriptor_loop_length)

    section_length = len(body) - 3 + 4
    body[1] = 0x70 | ((section_length >> 8) & 0x0F)
    body[2] = section_length & 0xFF

    crc = _calc_crc32_mpeg(bytes(body))
    body += struct.pack(">I", crc)
    return bytes(body)


@dataclass
class SCTE35Payload:
    binary: bytes
    hex: str
    base64: str
    splice_type: str
    pts_time: float | None
    splice_event_id: int

    @classmethod
    def from_splice_insert(
        cls,
        splice_event_id: int,
        pts_time: float | None = None,
        duration_secs: float | None = None,
        out_of_network: bool = True,
    ) -> "SCTE35Payload":
        binary = build_splice_insert(
            splice_event_id=splice_event_id,
            pts_time=pts_time,
            duration_secs=duration_secs,
            out_of_network=out_of_network,
        )
        return cls(
            binary=binary,
            hex=binary.hex(),
            base64=base64.b64encode(binary).decode(),
            splice_type="splice_insert",
            pts_time=pts_time,
            splice_event_id=splice_event_id,
        )

    @classmethod
    def from_time_signal(cls, splice_event_id: int, pts_time: float) -> "SCTE35Payload":
        binary = build_time_signal(splice_event_id=splice_event_id, pts_time=pts_time)
        return cls(
            binary=binary,
            hex=binary.hex(),
            base64=base64.b64encode(binary).decode(),
            splice_type="time_signal",
            pts_time=pts_time,
            splice_event_id=splice_event_id,
        )
