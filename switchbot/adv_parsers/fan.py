"""Fan adv parser."""

from __future__ import annotations

from ..const.fan import CirculatorFanProMode, FanMode, StandingFanMode

_FAN_MODE_MAP: dict[int, str] = {m.value: m.name.lower() for m in FanMode}
_STANDING_FAN_MODE_MAP: dict[int, str] = {
    m.value: m.name.lower() for m in StandingFanMode
}
_CIRCULATOR_FAN_PRO_MODE_MAP: dict[int, str] = {
    m.value: m.name.lower() for m in CirculatorFanProMode
}


def _parse_fan(
    mfr_data: bytes | None,
    mode_map: dict[int, str],
    *,
    with_charging: bool = False,
) -> dict[str, bool | int | str | None]:
    """Shared fan advertisement parse, parameterized on the mode map."""
    if mfr_data is None or len(mfr_data) < 10:
        return {}

    device_data = mfr_data[6:]

    _seq_num = device_data[0]
    _isOn = bool(device_data[1] & 0b10000000)
    _mode = (device_data[1] & 0b01110000) >> 4
    _nightLight = (device_data[1] & 0b00001100) >> 2
    _oscillate_left_and_right = bool(device_data[1] & 0b00000010)
    _oscillate_up_and_down = bool(device_data[1] & 0b00000001)
    _battery = device_data[2] & 0b01111111
    _speed = device_data[3] & 0b01111111

    result: dict[str, bool | int | str | None] = {
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
    if with_charging:
        # Bit 7 of the battery byte is the charging flag (Standing Fan only).
        result["charging"] = bool(device_data[2] & 0b10000000)
    return result


def process_fan(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str | None]:
    """Process Circulator Fan services data (modes 1-4)."""
    return _parse_fan(mfr_data, _FAN_MODE_MAP)


def process_standing_fan(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str | None]:
    """Process Standing Fan services data (modes 1-5; adds CUSTOM_NATURAL)."""
    return _parse_fan(mfr_data, _STANDING_FAN_MODE_MAP, with_charging=True)


def process_circulator_fan_pro(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str | None]:
    """
    Process Circulator Fan Pro (W1160) advertisement.

    The Pro shares the W1071 Modern Ceiling Fan broadcast layout, which differs
    from the legacy Circulator Fan: battery and the fan-state byte are swapped.
    The fan-state byte carries a two-level night light (bit2 = on/off, bit3 =
    level: 0 high / 1 low). Byte offsets are relative to the manufacturer data,
    after the leading 6-byte MAC.
    """
    if mfr_data is None or len(mfr_data) < 10:
        return {}

    device_data = mfr_data[6:]

    _seq_num = device_data[0]
    _charging = bool(device_data[1] & 0b10000000)
    _battery = device_data[1] & 0b01111111
    _state = device_data[2]
    _isOn = bool(_state & 0b10000000)
    _mode = (_state & 0b01110000) >> 4
    _night_light_on = bool(_state & 0b00000100)
    # bit3: 0 = level 1 (high / bright), 1 = level 2 (low / dim)
    _night_light_level = 2 if _state & 0b00001000 else 1
    _oscillate_left_and_right = bool(_state & 0b00000010)
    _oscillate_up_and_down = bool(_state & 0b00000001)
    _speed = device_data[3] & 0b01111111

    return {
        "sequence_number": _seq_num,
        "isOn": _isOn,
        "mode": _CIRCULATOR_FAN_PRO_MODE_MAP.get(_mode),
        "night_light_is_on": _night_light_on,
        "night_light_level": _night_light_level if _night_light_on else 0,
        "oscillating": _oscillate_left_and_right or _oscillate_up_and_down,
        "oscillating_horizontal": _oscillate_left_and_right,
        "oscillating_vertical": _oscillate_up_and_down,
        "battery": _battery,
        "charging": _charging,
        "speed": _speed,
    }

