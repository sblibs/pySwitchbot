"""Air Purifier adv parser."""

from __future__ import annotations

import struct

from ..const.air_purifier import AirPurifierMode, AirQualityLevel


def process_air_purifier(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process air purifier services data."""
    if mfr_data is None:
        return {}
    device_data = mfr_data[6:]

    _seq_num = device_data[0]
    _isOn = bool(device_data[1] & 0b10000000)
    _mode = device_data[1] & 0b00000111
    _is_aqi_valid = bool(device_data[2] & 0b00000100)
    _child_lock = bool(device_data[2] & 0b00000010)
    _speed = device_data[3] & 0b01111111
    _aqi_level = (device_data[4] & 0b00000110) >> 1
    _aqi_level = AirQualityLevel(_aqi_level).name.lower()
    _work_time = struct.unpack(">H", device_data[5:7])[0]
    _err_code = device_data[7]

    return {
        "isOn": _isOn,
        "mode": get_air_purifier_mode(_mode, _speed),
        "isAqiValid": _is_aqi_valid,
        "child_lock": _child_lock,
        "speed": _speed,
        "aqi_level": _aqi_level,
        "filter element working time": _work_time,
        "err_code": _err_code,
        "sequence_number": _seq_num,
    }


def get_air_purifier_mode(mode: int, speed: int) -> str | None:
    if mode == 1:
        if 0 <= speed <= 33:
            return "level_1"
        if 34 <= speed <= 66:
            return "level_2"
        return "level_3"
    if 1 < mode <= 4:
        mode += 2
        return AirPurifierMode(mode).name.lower()
    return None
