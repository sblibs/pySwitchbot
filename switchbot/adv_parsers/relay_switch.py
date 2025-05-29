"""Relay Switch adv parser."""

from __future__ import annotations

from typing import Any


def process_relay_switch_common_data(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, Any]:
    """Process relay switch 1 and 1PM common data."""
    if mfr_data is None:
        return {}
    return {
        "switchMode": True,  # for compatibility, useless
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
    }


def process_garage_door_opener(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, Any]:
    """Process garage door opener services data."""
    if mfr_data is None:
        return {}
    common_data = process_relay_switch_common_data(data, mfr_data)
    common_data["door_open"] = not bool(mfr_data[7] & 0b00100000)
    return common_data


def process_relay_switch_2pm(
    data: bytes | None, mfr_data: bytes | None
) -> dict[int, dict[str, Any]]:
    """Process Relay Switch 2PM services data."""
    if mfr_data is None:
        return {}

    return {
        1: {
            **process_relay_switch_common_data(data, mfr_data),
        },
        2: {
            "switchMode": True,  # for compatibility, useless
            "sequence_number": mfr_data[6],
            "isOn": bool(mfr_data[7] & 0b01000000),
        },
    }
