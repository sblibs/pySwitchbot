"""Advertisement data parser for climate panel devices."""

import logging

_LOGGER = logging.getLogger(__name__)


def process_climate_panel(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Climate Panel data."""
    if mfr_data is None or len(mfr_data) < 16:
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
    is_light = ((mfr_data[15] >> 1) & 0x03) == 0x02

    # Keystate bytes report physical ON/OFF button presses. For each byte,
    # Bit[7:5] is the press mode (0: power-on init, 1: single, 2: double,
    # 3: long) and Bit[4:0] is a 1-30 cyclic counter that resets to 1 when the
    # mode changes. A value of 0x00 is the power-on state and must not trigger.
    # The raw byte is also exposed so consumers can watch it for any change.
    on_keystate = mfr_data[13]
    off_keystate = mfr_data[14]
    on_keystate_mode = (on_keystate >> 5) & 0x07
    on_keystate_counter = on_keystate & 0x1F
    off_keystate_mode = (off_keystate >> 5) & 0x07
    off_keystate_counter = off_keystate & 0x1F

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
        "on_keystate": on_keystate,
        "off_keystate": off_keystate,
        "on_keystate_mode": on_keystate_mode,
        "on_keystate_counter": on_keystate_counter,
        "off_keystate_mode": off_keystate_mode,
        "off_keystate_counter": off_keystate_counter,
    }

    _LOGGER.debug(
        "Processed climate panel mfr data: %s, result: %s", mfr_data.hex(), result
    )
    return result
