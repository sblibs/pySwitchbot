"""Humidifier adv parser."""

from __future__ import annotations

import logging
from datetime import timedelta

from ..const.evaporative_humidifier import (
    HumidifierMode,
    HumidifierWaterLevel,
)
from ..helpers import celsius_to_fahrenheit

_LOGGER = logging.getLogger(__name__)

# mfr_data: 943cc68d3d2e
# data: 650000cd802b6300
# data: 650000cd802b6300
# data: 658000c9802b6300


# Low:  658000c5222b6300
# Med:  658000c5432b6300
# High: 658000c5642b6300


def calculate_temperature_and_humidity(
    data: bytes, is_meter_binded: bool = True
) -> tuple[float | None, float | None, int | None]:
    """Calculate temperature and humidity based on the given flag."""
    if len(data) < 3 or not is_meter_binded:
        return None, None, None

    humidity = data[0] & 0b01111111
    if humidity > 100:
        return None, None, None

    _temp_sign = 1 if data[1] & 0b10000000 else -1
    _temp_c = _temp_sign * ((data[1] & 0b01111111) + ((data[2] >> 4) / 10))
    _temp_f = celsius_to_fahrenheit(_temp_c)

    return _temp_c, _temp_f, humidity


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
        return {}

    seq_number = mfr_data[6]
    is_on = bool(mfr_data[7] & 0b10000000)
    mode = HumidifierMode(mfr_data[7] & 0b00001111)
    over_humidify_protection = bool(mfr_data[8] & 0b10000000)
    child_lock = bool(mfr_data[8] & 0b00100000)
    tank_removed = bool(mfr_data[8] & 0b00000100)
    tilted_alert = bool(mfr_data[8] & 0b00000010)
    filter_missing = bool(mfr_data[8] & 0b00000001)
    is_meter_binded = bool(mfr_data[9] & 0b10000000)

    _temp_c, _temp_f, humidity = calculate_temperature_and_humidity(
        mfr_data[9:12], is_meter_binded
    )

    water_level = HumidifierWaterLevel(mfr_data[11] & 0b00000011).name.lower()
    filter_run_time = timedelta(
        hours=int.from_bytes(mfr_data[12:14], byteorder="big") & 0xFFF
    )
    target_humidity = mfr_data[16] & 0b01111111

    return {
        "seq_number": seq_number,
        "isOn": is_on,
        "mode": mode,
        "over_humidify_protection": over_humidify_protection,
        "child_lock": child_lock,
        "tank_removed": tank_removed,
        "tilted_alert": tilted_alert,
        "filter_missing": filter_missing,
        "is_meter_binded": is_meter_binded,
        "humidity": humidity,
        "temperature": _temp_c,
        "temp": {"c": _temp_c, "f": _temp_f},
        "water_level": water_level,
        "filter_run_time": filter_run_time,
        "filter_alert": filter_run_time.days >= 10,
        "target_humidity": target_humidity,
    }
