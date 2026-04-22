"""Fan adv parser."""

from __future__ import annotations

from ..const.fan import StandingFanMode


def process_fan(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """
    Process fan services data.

    Shared parser for Circulator Fan and Standing Fan. The mode field covers
    values 1-4 for the Circulator Fan and 1-5 for the Standing Fan
    (CUSTOM_NATURAL = 5). StandingFanMode is used for the mapping because its
    names are a superset of FanMode for values 1-4.
    """
    if mfr_data is None:
        return {}

    device_data = mfr_data[6:]

    _seq_num = device_data[0]
    _isOn = bool(device_data[1] & 0b10000000)
    _mode = (device_data[1] & 0b01110000) >> 4
    _mode = StandingFanMode(_mode).name.lower() if 1 <= _mode <= 5 else None
    _nightLight = (device_data[1] & 0b00001100) >> 2
    _oscillate_left_and_right = bool(device_data[1] & 0b00000010)
    _oscillate_up_and_down = bool(device_data[1] & 0b00000001)
    _battery = device_data[2] & 0b01111111
    _speed = device_data[3] & 0b01111111

    return {
        "sequence_number": _seq_num,
        "isOn": _isOn,
        "mode": _mode,
        "nightLight": _nightLight,
        "oscillating": _oscillate_left_and_right or _oscillate_up_and_down,
        "oscillating_horizontal": _oscillate_left_and_right,
        "oscillating_vertical": _oscillate_up_and_down,
        "battery": _battery,
        "speed": _speed,
    }
