"""Hub2 parser."""

from __future__ import annotations

from typing import Any


def process_wohub2(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process woHub2 sensor manufacturer data."""
    temp_data = None

    if mfr_data:
        status = mfr_data[12]
        temp_data = mfr_data[13:16]

    if not temp_data:
        return {}

    _temp_sign = 1 if temp_data[1] & 0b10000000 else -1
    _temp_c = _temp_sign * (
        (temp_data[1] & 0b01111111) + ((temp_data[0] & 0b00001111) / 10)
    )
    _temp_f = (_temp_c * 9 / 5) + 32
    _temp_f = (_temp_f * 10) / 10
    humidity = temp_data[2] & 0b01111111
    light_level = status & 0b11111

    if _temp_c == 0 and humidity == 0:
        return {}

    _wohub2_data = {
        # Data should be flat, but we keep the original structure for now
        "temp": {"c": _temp_c, "f": _temp_f},
        "temperature": _temp_c,
        "fahrenheit": bool(temp_data[2] & 0b10000000),
        "humidity": humidity,
        "lightLevel": light_level,
        "illuminance": calculate_light_intensity(light_level),
    }

    return _wohub2_data


def calculate_light_intensity(light_level: int) -> int:
    """
    Convert Hub 2 light level (1-21) to actual light intensity value
    Args:
        light_level: Integer from 1-21
    Returns:
        Corresponding light intensity value or 0 if invalid input
    """
    light_map = {
        1: 0,
        2: 10,
        3: 20,
        4: 30,
        5: 40,
        6: 50,
        7: 60,
        8: 70,
        9: 80,
        10: 90,
        11: 105,
        12: 205,
        13: 317,
        14: 416,
        15: 510,
        16: 610,
        17: 707,
        18: 801,
        19: 897,
        20: 1023,
        21: 1091,
    }

    if not isinstance(light_level, int) or light_level < 1 or light_level > 21:
        return 0
    return light_map[light_level]
