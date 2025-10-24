"""Smart Thermostat Radiator"""

import logging

from ..const.climate import SmartThermostatRadiatorMode

_LOGGER = logging.getLogger(__name__)


def process_smart_thermostat_radiator(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Smart Thermostat Radiator data."""
    if mfr_data is None:
        return {}

    _seq_num = mfr_data[6]
    _isOn = bool(mfr_data[7] & 0b10000000)
    _battery = mfr_data[7] & 0b01111111

    temp_data = mfr_data[8:11]
    target_decimal = (temp_data[0] >> 4) & 0x0F
    local_decimal = temp_data[0] & 0x0F

    local_sign = 1 if (temp_data[1] & 0x80) else -1
    local_int = temp_data[1] & 0x7F
    local_temp = local_sign * (local_int + (local_decimal / 10))

    target_sign = 1 if (temp_data[2] & 0x80) else -1
    target_int = temp_data[2] & 0x7F
    target_temp = target_sign * (target_int + (target_decimal / 10))

    last_mode = SmartThermostatRadiatorMode.get_mode_name((mfr_data[11] >> 4) & 0x0F)
    mode = SmartThermostatRadiatorMode.get_mode_name(mfr_data[11] & 0x07)

    need_update_temp = bool((mfr_data[12] >> 5) & 0x01)
    restarted = bool((mfr_data[12] >> 4) & 0x01)
    fault_code = (mfr_data[12] >> 1) & 0x07
    door_open = bool(mfr_data[12] & 0x01)

    result = {
        "sequence_number": _seq_num,
        "isOn": _isOn,
        "battery": _battery,
        "temperature": local_temp,
        "target_temperature": target_temp,
        "mode": mode,
        "last_mode": last_mode,
        "need_update_temp": need_update_temp,
        "restarted": restarted,
        "fault_code": fault_code,
        "door_open": door_open,
    }

    _LOGGER.debug(
        "Smart Thermostat Radiator mfr data: %s, result: %s", mfr_data.hex(), result
    )
    return result
