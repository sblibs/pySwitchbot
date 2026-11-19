"""Light strip adv parser."""

from __future__ import annotations

from ..helpers import _UNPACK_UINT16_BE


def process_wostrip(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoStrip services data."""
    if mfr_data is None or len(mfr_data) < 9:
        return {}
    return {
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "brightness": mfr_data[7] & 0b01111111,
        "delay": bool(mfr_data[8] & 0b10000000),
        "network_state": (mfr_data[8] & 0b01110000) >> 4,
        "color_mode": mfr_data[8] & 0b00001111,
    }


def process_candle_warmer_lamp(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process Candle Warmer Lamp services data."""
    if mfr_data is None or len(mfr_data) < 9:
        return {}
    return {
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "brightness": mfr_data[7] & 0b01111111,
        "delay": bool(mfr_data[8] & 0b10000000),
        "network_state": (mfr_data[8] & 0b01110000) >> 4,
    }


def process_light(
    data: bytes | None, mfr_data: bytes | None, cw_offset: int = 16
) -> dict[str, bool | int]:
    """Support for strip light 3 and floor lamp."""
    common_data = process_wostrip(data, mfr_data)
    if not common_data or len(mfr_data) < cw_offset + 2:
        return {}

    light_data = {"cw": _UNPACK_UINT16_BE(mfr_data, cw_offset)[0]}

    return common_data | light_data


def process_rgbic_light(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Support for RGBIC lights."""
    return process_light(data, mfr_data, cw_offset=10)


def process_rgbicww_ceiling_light(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Support for RGBICWW Ceiling Light (white + color sub-lights)."""
    common_data = process_light(data, mfr_data, cw_offset=10)
    if not common_data or len(mfr_data) < 14:
        return {}
    return common_data | {
        "main_isOn": bool(mfr_data[13] & 0b10000000),
        "main_brightness": mfr_data[13] & 0b01111111,
    }
