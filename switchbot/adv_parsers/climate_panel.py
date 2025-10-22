"""Advertisement data parser for climate panel devices."""

import logging

_LOGGER = logging.getLogger(__name__)


def process_climate_panel(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Climate Panel data."""
    if mfr_data is None:
        return {}

    seq_number = mfr_data[6]
    isOn = bool(mfr_data[7] & 0x80)
    battery = mfr_data[7] & 0x7F
    humidity_alarm = (mfr_data[8] >> 6) & 0x03
    temp_alarm = (mfr_data[8] >> 4) & 0x03

    temp_decimal = mfr_data[8] & 0x0F
    temp_sign = 1 if (mfr_data[9] & 0x80) else -1
    temp_int = mfr_data[9] & 0x7F
    temperature = temp_sign * (temp_int + temp_decimal / 10)

    humidity = mfr_data[10] & 0x7F

    pir_state = bool(mfr_data[15] & 0x80)
    is_light = ((mfr_data[15] >> 2) & 0x03) == 0x10

    result = {
        "sequence_number": seq_number,
        "isOn": isOn,
        "battery": battery,
        "temperature": temperature,
        "humidity": humidity,
        "temp_alarm": temp_alarm,
        "humidity_alarm": humidity_alarm,
        "motion_detected": pir_state,
        "is_light": is_light,
    }

    _LOGGER.debug(
        "Processed climate panel mfr data: %s, result: %s", mfr_data.hex(), result
    )
    return result
