"""Shared temperature/humidity decoding helpers for T/H sensors."""

from __future__ import annotations

from typing import Any

from ..helpers import celsius_to_fahrenheit


def decode_temp_humidity(temp_data: bytes, battery: int | None) -> dict[str, Any]:
    """
    Decode temperature/humidity/fahrenheit-flag from a 3-byte payload.

    Layout (bytes after company ID, for SwitchBot T/H sensors):
        byte 0: bits[3:0] = temperature decimal (0.1 °C units)
        byte 1: bit[7] = temperature sign (1 = positive), bits[6:0] = integer °C
        byte 2: bit[7] = fahrenheit-display flag, bits[6:0] = humidity %
    """
    _temp_sign = 1 if temp_data[1] & 0b10000000 else -1
    _temp_c = _temp_sign * (
        (temp_data[1] & 0b01111111) + ((temp_data[0] & 0b00001111) / 10)
    )
    _temp_f = celsius_to_fahrenheit(_temp_c)
    _temp_f = (_temp_f * 10) / 10
    humidity = temp_data[2] & 0b01111111

    if _temp_c == 0 and humidity == 0 and battery == 0:
        return {}

    return {
        "temp": {"c": _temp_c, "f": _temp_f},
        "temperature": _temp_c,
        "fahrenheit": bool(temp_data[2] & 0b10000000),
        "humidity": humidity,
        "battery": battery,
    }
