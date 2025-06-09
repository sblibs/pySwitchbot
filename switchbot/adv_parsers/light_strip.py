"""Light strip adv parser."""

from __future__ import annotations

import struct


def process_wostrip(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoStrip services data."""
    if mfr_data is None:
        return {}
    return {
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "brightness": mfr_data[7] & 0b01111111,
        "delay": bool(mfr_data[8] & 0b10000000),
        "network_state": (mfr_data[8] & 0b01110000) >> 4,
        "color_mode": mfr_data[8] & 0b00001111,
    }


def process_light(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Support for strip light 3 and floor lamp."""
    common_data = process_wostrip(data, mfr_data)
    if not common_data:
        return {}

    light_data = {"cw": struct.unpack(">H", mfr_data[16:18])[0]}

    return common_data | light_data
