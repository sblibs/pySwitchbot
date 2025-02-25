"""Humidifier adv parser."""

from __future__ import annotations

import logging
from datetime import timedelta

from ..const.evaporative_humidifier import (
    OVER_HUMIDIFY_PROTECTION_MODES,
    TARGET_HUMIDITY_MODES,
    HumidifierMode,
    HumidifierWaterLevel,
)

_LOGGER = logging.getLogger(__name__)

# mfr_data: 943cc68d3d2e
# data: 650000cd802b6300
# data: 650000cd802b6300
# data: 658000c9802b6300


# Low:  658000c5222b6300
# Med:  658000c5432b6300
# High: 658000c5642b6300
def process_wohumidifier(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoHumi services data."""
    if data is None:
        return {
            "isOn": None,
            "level": None,
            "switchMode": True,
        }

    return {
        "isOn": bool(data[1]),
        "level": data[4],
        "switchMode": True,
    }


def process_evaporative_humidifier(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoHumi services data."""
    if mfr_data is None:
        return {
            "isOn": None,
            "mode": None,
            "target_humidity": None,
            "child_lock": None,
            "over_humidify_protection": None,
            "tank_removed": None,
            "tilted_alert": None,
            "filter_missing": None,
            "humidity": None,
            "temperature": None,
            "filter_run_time": None,
            "filter_alert": None,
            "water_level": None,
        }

    is_on = bool(mfr_data[7] & 0b10000000)
    mode = HumidifierMode(mfr_data[7] & 0b00001111)
    filter_run_time = timedelta(hours=int.from_bytes(mfr_data[12:14], byteorder="big"))
    has_humidity = bool(mfr_data[9] & 0b10000000)
    has_temperature = bool(mfr_data[10] & 0b10000000)
    is_tank_removed = bool(mfr_data[8] & 0b00000100)
    return {
        "isOn": is_on,
        "mode": mode if is_on else None,
        "target_humidity": (mfr_data[16] & 0b01111111)
        if is_on and mode in TARGET_HUMIDITY_MODES
        else None,
        "child_lock": bool(mfr_data[8] & 0b00100000),
        "over_humidify_protection": bool(mfr_data[8] & 0b10000000)
        if is_on and mode in OVER_HUMIDIFY_PROTECTION_MODES
        else None,
        "tank_removed": is_tank_removed,
        "tilted_alert": bool(mfr_data[8] & 0b00000010),
        "filter_missing": bool(mfr_data[8] & 0b00000001),
        "humidity": (mfr_data[9] & 0b01111111) if has_humidity else None,
        "temperature": float(mfr_data[10] & 0b01111111) + float(mfr_data[11] >> 4) / 10
        if has_temperature
        else None,
        "filter_run_time": filter_run_time,
        "filter_alert": filter_run_time.days >= 10,
        "water_level": HumidifierWaterLevel(mfr_data[11] & 0b00000011)
        if not is_tank_removed
        else None,
    }
