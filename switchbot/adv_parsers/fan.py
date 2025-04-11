"""Fan adv parser."""

from __future__ import annotations

from ..const.fan import FanMode


def process_fan(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process fan services data."""
    if mfr_data is None:
        return {}

    device_data = mfr_data[6:]

    _seq_num = device_data[0]
    _isOn = bool(device_data[1] & 0b10000000)
    _mode = (device_data[1] & 0b01110000) >> 4
    _mode = FanMode(_mode).name if 1 <= _mode <= 4 else None
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
        "oscillating": _oscillate_left_and_right | _oscillate_up_and_down,
        "battery": _battery,
        "speed": _speed,
    }
