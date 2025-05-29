"""Hub3 adv parser."""

from __future__ import annotations

from typing import Any

from ..const.hub3 import LIGHT_INTENSITY_MAP
from ..helpers import celsius_to_fahrenheit


def process_hub3(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process hub3 sensor manufacturer data."""
    if mfr_data is None:
        return {}
    device_data = mfr_data[6:]

    seq_num = device_data[0]
    network_state = (device_data[6] & 0b11000000) >> 6
    sensor_inserted = not bool(device_data[6] & 0b00100000)
    light_level = device_data[6] & 0b00001111
    illuminance = calculate_light_intensity(light_level)
    temperature_alarm = bool(device_data[7] & 0b11000000)
    humidity_alarm = bool(device_data[7] & 0b00110000)

    temp_data = device_data[7:10]
    _temp_sign = 1 if temp_data[1] & 0b10000000 else -1
    _temp_c = _temp_sign * (
        (temp_data[1] & 0b01111111) + ((temp_data[0] & 0b00001111) / 10)
    )
    _temp_f = round(celsius_to_fahrenheit(_temp_c), 1)
    humidity = temp_data[2] & 0b01111111
    motion_detected = bool(device_data[10] & 0b10000000)

    return {
        "sequence_number": seq_num,
        "network_state": network_state,
        "sensor_inserted": sensor_inserted,
        "lightLevel": light_level,
        "illuminance": illuminance,
        "temperature_alarm": temperature_alarm,
        "humidity_alarm": humidity_alarm,
        "temp": {"c": _temp_c, "f": _temp_f},
        "temperature": _temp_c,
        "humidity": humidity,
        "motion_detected": motion_detected,
    }


def calculate_light_intensity(light_level: int) -> int:
    """
    Convert Hub 3 light level (1-10) to actual light intensity value
    Args:
        light_level: Integer from 1-10
    Returns:
        Corresponding light intensity value or 0 if invalid input
    """
    return LIGHT_INTENSITY_MAP.get(max(0, min(light_level, 10)), 0)
