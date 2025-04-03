"""Library to handle connection with Switchbot."""

from __future__ import annotations


def process_worollershade(
    data: bytes | None, mfr_data: bytes | None, reverse: bool = True
) -> dict[str, bool | int]:
    """Process woRollerShade services data."""
    if mfr_data is None:
        return {}

    device_data = mfr_data[6:]

    _position = max(min(device_data[2] & 0b01111111, 100), 0)
    _calibrated = bool(device_data[2] & 0b10000000)
    _in_motion = bool(device_data[1] & 0b00000110)
    _light_level = (device_data[3] >> 4) & 0b00001111
    _device_chain = device_data[3] & 0b00001111

    return {
        "calibration": _calibrated,
        "battery": data[2] & 0b01111111 if data else None,
        "inMotion": _in_motion,
        "position": (100 - _position) if reverse else _position,
        "lightLevel": _light_level,
        "deviceChain": _device_chain,
        "sequence_number": device_data[0],
    }
