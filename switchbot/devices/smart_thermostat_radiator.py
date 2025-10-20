"""Smart Thermostat Radiator Device."""

import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..models import SwitchBotAdvertisement
from .base_cover import CONTROL_SOURCE, SwitchbotBaseCover
from .device import (
    REQ_HEADER,
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)
from ..const.climate import SmartThermostatRadiatorMode, ClimateMode
from .base_cliamte import SwitchbotBaseClimate

_LOGGER = logging.getLogger(__name__)

DEVICE_GET_BASIC_SETTINGS_KEY = "5702"

_SMART_THERMOSTAT_RADIATOR_MODE_MAP = {
    SmartThermostatRadiatorMode.AUTO: ClimateMode.HEAT,
    SmartThermostatRadiatorMode.MANUAL: ClimateMode.HEAT,
    SmartThermostatRadiatorMode.OFF: ClimateMode.OFF,
    SmartThermostatRadiatorMode.ECONOMIC: ClimateMode.HEAT,
    SmartThermostatRadiatorMode.COMFORT: ClimateMode.HEAT,
    SmartThermostatRadiatorMode.FAST_HEAT: ClimateMode.HEAT,
}


class SwitchbotSmartThermostatRadiator(SwitchbotBaseClimate, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Smart Thermostat Radiator."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.SMART_THERMOSTAT_RADIATOR,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.SMART_THERMOSTAT_RADIATOR,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    @property
    def hvac_modes(self) -> set[ClimateMode]:
        """Return the supported hvac modes."""
        return {ClimateMode.HEAT, ClimateMode.OFF}

    @property
    def hvac_mode(self) -> ClimateMode | None:
        """Return the current hvac mode."""
        return _SMART_THERMOSTAT_RADIATOR_MODE_MAP.get(self.get_current_mode(), ClimateMode.OFF)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.get_current_temperature()

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.get_target_temperature()

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        _LOGGER.debug("data: %s", _data)

        battery = _data[1]
        firmware = _data[2] / 10.0
        hardware = _data[3]
        last_mode = SmartThermostatRadiatorMode.get_mode_name((_data[4] >> 3) & 0x07)
        mode = SmartThermostatRadiatorMode.get_mode_name(_data[4] & 0x07)
        temp_raw_value = _data[5] << 8 | _data[6]
        temp_sign = 1 if temp_raw_value >> 15 else -1
        temperature = temp_sign * (temp_raw_value & 0x7FFF) / 10.0
        manual_target_temp = (_data[7] << 8 | _data[8]) / 10.0
        comfort_target_temp = _data[9] / 10.0
        economic_target_temp = _data[10] / 10.0
        fast_heat_time = _data[11]
        child_lock = bool(_data[12] & 0x03)
        target_temp = (_data[13] << 8 | _data[14]) / 10.0
        door_open = bool(_data[14] & 0x01)

        result = {
            "battery": battery,
            "firmware": firmware,
            "hardware": hardware,
            "last_mode": last_mode,
            "mode": mode,
            "temperature": temperature,
            "manual_target_temp": manual_target_temp,
            "comfort_target_temp": comfort_target_temp,
            "economic_target_temp": economic_target_temp,
            "fast_heat_time": fast_heat_time,
            "child_lock": child_lock,
            "target_temp": target_temp,
            "door_open": door_open,
        }

        _LOGGER.debug("Smart Thermostat Radiator basic info: %s", result)
        return result

    def is_on(self) -> bool | None:
        """Return true if the thermostat is on."""
        return self._get_adv_value("isOn")

    def get_current_mode(self) -> str | None:
        """Return the current mode of the thermostat."""
        return self._get_adv_value("mode")

    def door_open(self) -> bool | None:
        """Return true if the door is open."""
        return self._get_adv_value("door_open")

    def get_current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._get_adv_value("temperature")

    def get_target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._get_adv_value("target_temperature")
