"""Advertisement data parser for presence sensor devices."""

from __future__ import annotations

import logging

from ..const.presence_sensor import BATTERY_LEVEL_MAP

_LOGGER = logging.getLogger(__name__)


def process_presence_sensor(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Presence Sensor data."""
    if mfr_data is None:
        return {}

    seq_number = mfr_data[6]
    adaptive_state = bool(mfr_data[7] & 0x80)
    motion_detected = bool(mfr_data[7] & 0x40)
    battery_bits = (mfr_data[7] >> 2) & 0x03
    battery_range = BATTERY_LEVEL_MAP.get(battery_bits, "Unknown")
    duration = (mfr_data[8] << 8) + mfr_data[9]
    trigger_flag = mfr_data[10]
    led_state = bool(mfr_data[11] & 0x80)
    light_level = mfr_data[11] & 0x1F

    result = {
        "sequence_number": seq_number,
        "adaptive_state": adaptive_state,
        "motion_detected": motion_detected,
        "battery_range": battery_range,
        "duration": duration,
        "trigger_flag": trigger_flag,
        "led_state": led_state,
        "lightLevel": light_level,
    }

    if data:
        battery = data[2] & 0x7F
        result["battery"] = battery

    _LOGGER.debug(
        "Processed presence sensor mfr data: %s, result: %s", mfr_data.hex(), result
    )
    return result
