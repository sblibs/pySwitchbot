"""Library to handle connection with Switchbot."""

from __future__ import annotations

from ..helpers import parse_power_data


def process_woplugmini(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process plug mini."""
    if mfr_data is None:
        return {}
    return {
        "switchMode": True,
        "isOn": mfr_data[7] == 0x80,
        "wifi_rssi": -mfr_data[9],
        "power": parse_power_data(mfr_data, 10, 10.0, 0x7FFF),  # W
    }
