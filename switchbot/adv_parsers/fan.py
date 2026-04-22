"""Fan adv parser."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from ..const.fan import FanMode, StandingFanMode

if TYPE_CHECKING:
    from collections.abc import Mapping


def _parse_fan(
    mfr_data: bytes | None, mode_enum: type[Enum]
) -> dict[str, bool | int | str | None]:
    """Shared fan advertisement parse, parameterized on the mode enum."""
    if mfr_data is None:
        return {}

    device_data = mfr_data[6:]

    _seq_num = device_data[0]
    _isOn = bool(device_data[1] & 0b10000000)
    _mode = (device_data[1] & 0b01110000) >> 4
    mode_map: Mapping[int, str] = {m.value: m.name.lower() for m in mode_enum}
    _nightLight = (device_data[1] & 0b00001100) >> 2
    _oscillate_left_and_right = bool(device_data[1] & 0b00000010)
    _oscillate_up_and_down = bool(device_data[1] & 0b00000001)
    _battery = device_data[2] & 0b01111111
    _speed = device_data[3] & 0b01111111

    return {
        "sequence_number": _seq_num,
        "isOn": _isOn,
        "mode": mode_map.get(_mode),
        "nightLight": _nightLight,
        "oscillating": _oscillate_left_and_right or _oscillate_up_and_down,
        "oscillating_horizontal": _oscillate_left_and_right,
        "oscillating_vertical": _oscillate_up_and_down,
        "battery": _battery,
        "speed": _speed,
    }


def process_fan(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str | None]:
    """Process Circulator Fan services data (modes 1-4)."""
    return _parse_fan(mfr_data, FanMode)


def process_standing_fan(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str | None]:
    """Process Standing Fan services data (modes 1-5; adds CUSTOM_NATURAL)."""
    return _parse_fan(mfr_data, StandingFanMode)
