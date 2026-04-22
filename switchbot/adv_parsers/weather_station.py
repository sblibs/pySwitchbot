"""Weather Station parser."""

from __future__ import annotations

from typing import Any

from ._sensor_th import decode_temp_humidity


def process_weather_station(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, Any]:
    """
    Process Weather Station advertisement data.

    Manufacturer data layout (mfr_id=2409, after company ID stripped by bleak):
        Byte 0-5: MAC address
        Byte 6:   Sequence number
        Byte 7:   Battery (bit7=charging, bit6-0=level%)
        Byte 8:   Temp alarm(bit7-6), Humidity alarm(bit5-4), Temp decimal(bit3-0)
        Byte 9:   Temp sign(bit7: 0=neg,1=pos), Temp integer(bit6-0)
        Byte 10:  Fahrenheit flag(bit7), Humidity(bit6-0)
    """
    temp_data: bytes | None = None
    battery: int | None = None

    if mfr_data and len(mfr_data) >= 11:
        temp_data = mfr_data[8:11]
        battery = mfr_data[7] & 0b01111111

    if data and len(data) >= 6:
        if not temp_data:
            temp_data = data[3:6]
        if battery is None:
            battery = data[2] & 0b01111111

    if not temp_data:
        return {}

    return decode_temp_humidity(temp_data, battery)
