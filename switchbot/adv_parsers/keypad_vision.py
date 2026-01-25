"""Keypad Vision (Pro) device data parsers."""

import logging

_LOGGER = logging.getLogger(__name__)


def process_common_mfr_data(mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process common Keypad Vision (Pro) manufacturer data."""
    if mfr_data is None:
        return {}

    sequence_number = mfr_data[6]
    battery_charging = bool(mfr_data[7] & 0b10000000)
    battery = mfr_data[7] & 0b01111111
    lockout_alarm = bool(mfr_data[8] & 0b00000001)
    tamper_alarm = bool(mfr_data[8] & 0b00000010)
    duress_alarm = bool(mfr_data[8] & 0b00000100)
    low_temperature = bool(mfr_data[8] & 0b10000000)
    high_temperature = bool(mfr_data[8] & 0b01000000)
    doorbell = bool(mfr_data[12] & 0b00001000)

    return {
        "sequence_number": sequence_number,
        "battery_charging": battery_charging,
        "battery": battery,
        "lockout_alarm": lockout_alarm,
        "tamper_alarm": tamper_alarm,
        "duress_alarm": duress_alarm,
        "low_temperature": low_temperature,
        "high_temperature": high_temperature,
        "doorbell": doorbell,
    }


def process_keypad_vision(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Keypad Vision data."""
    result = process_common_mfr_data(mfr_data)

    if not result:
        return {}

    pir_triggered_level = mfr_data[13] & 0x03

    result.update(
        {
            "pir_triggered_level": pir_triggered_level,
        }
    )

    _LOGGER.debug("Keypad Vision mfr data: %s, result: %s", mfr_data.hex(), result)

    return result


def process_keypad_vision_pro(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Keypad Vision Pro data."""
    result = process_common_mfr_data(mfr_data)

    if not result:
        return {}

    radar_triggered_level = mfr_data[13] & 0x03
    radar_triggered_distance = (mfr_data[13] >> 2) & 0x03

    result.update(
        {
            "radar_triggered_level": radar_triggered_level,
            "radar_triggered_distance": radar_triggered_distance,
        }
    )

    _LOGGER.debug("Keypad Vision Pro mfr data: %s, result: %s", mfr_data.hex(), result)

    return result
