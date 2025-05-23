"""Relay Switch adv parser."""

from __future__ import annotations

import struct
from typing import Any


def parse_power_data(mfr_data: bytes, start: int, end: int) -> int:
    """Helper to parse power data from manufacturer data."""
    return struct.unpack(">H", mfr_data[start:end])[0] / 10.0


def process_relay_switch_common_data(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process relay switch common data."""
    if mfr_data is None:
        return {}
    return {
        "switchMode": True,  # for compatibility, useless
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
    }


def process_relay_switch_1pm(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process Relay Switch 1PM services data."""
    if mfr_data is None:
        return {}
    common_data = process_relay_switch_common_data(data, mfr_data)
    common_data["power"] = parse_power_data(mfr_data, 10, 12)
    common_data["voltage"] = 0
    common_data["current"] = 0
    return common_data


def process_garage_door_opener(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process garage door opener services data."""
    if mfr_data is None:
        return {}
    common_data = process_relay_switch_common_data(data, mfr_data)
    common_data["door_open"] = not bool(mfr_data[7] & 0b00100000)
    return common_data


def process_relay_switch_2pm(data: bytes | None, mfr_data: bytes | None) -> dict[int, dict[str, Any]]:
    """Process Relay Switch 2PM services data."""
    if mfr_data is None:
        return {}

    return {
        1: {
            **process_relay_switch_common_data(data, mfr_data),
            "power": parse_power_data(mfr_data, 10, 12),
            "voltage": 0,
            "current": 0,
        },
        2: {
            "switchMode": True,  # for compatibility, useless
            "sequence_number": mfr_data[6],
            "isOn": bool(mfr_data[7] & 0b01000000),
            "power": parse_power_data(mfr_data, 12, 14),
            "voltage": 0,
            "current": 0,
        },
    }




