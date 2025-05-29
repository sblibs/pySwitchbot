"""Switchbot Advertisement Parser Library."""


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
    _temp_f = (_temp_c * 9 / 5) + 32

    return _temp_c, _temp_f, humidity
