"""Meter parser."""

from __future__ import annotations

import struct
from typing import Any

from ._sensor_th import decode_temp_humidity

CO2_UNPACK = struct.Struct(">H").unpack_from

# Meter Pro CO2 sensor spec range is 400-9999 ppm. Higher values are
# transient parsing artifacts and surface as huge spikes downstream.
CO2_MAX_PPM = 9999


def process_wosensorth(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process woSensorTH/Temp sensor services data."""
    temp_data: bytes | None = None
    battery: int | None = None

    if mfr_data and len(mfr_data) >= 11:
        temp_data = mfr_data[8:11]

    if data and len(data) >= 3:
        if not temp_data and len(data) >= 6:
            temp_data = data[3:6]
        battery = data[2] & 0b01111111

    if not temp_data:
        return {}

    return decode_temp_humidity(temp_data, battery)


def process_wosensorth_c(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process woSensorTH/Temp sensor services data with CO2."""
    _wosensorth_data = process_wosensorth(data, mfr_data)
    if _wosensorth_data and mfr_data and len(mfr_data) >= 15:
        co2_data = mfr_data[13:15]
        co2 = CO2_UNPACK(co2_data)[0]
        if co2 <= CO2_MAX_PPM:
            _wosensorth_data["co2"] = co2
    return _wosensorth_data
