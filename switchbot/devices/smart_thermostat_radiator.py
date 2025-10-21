"""Smart Thermostat Radiator Device."""

import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.climate import ClimateAction, ClimateMode, SmartThermostatRadiatorMode
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_GET_BASIC_SETTINGS_KEY = "5702"

_modes = ["manual", "comfort", "economic", "fast_heating", "schedule"]
SMART_THERMOSTAT_TO_HA_HVAC_MODE = {"off": ClimateMode.OFF, **dict.fromkeys(_modes, ClimateMode.HEAT)}

COMMAND_SET_MODE = {
    mode.name.lower(): f"570F7800{index:02X}"
    for index, mode in enumerate(SmartThermostatRadiatorMode)
}
COMMAND_SET_TEMP = "570301{}ffffffff"

class SwitchbotSmartThermostatRadiator(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Smart Thermostat Radiator."""

    _turn_off_command = "570100"
    _turn_on_command = "570101"

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
    def min_temperature(self) -> float:
        """Return the minimum target temperature."""
        return 5.0

    @property
    def max_temperature(self) -> float:
        """Return the maximum target temperature."""
        return 35.0

    @property
    def preset_modes(self) -> list[str]:
        """Return the supported preset modes."""
        return SmartThermostatRadiatorMode.get_modes()

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self.get_current_mode()

    @property
    def hvac_modes(self) -> set[ClimateMode]:
        """Return the supported hvac modes."""
        return {ClimateMode.HEAT, ClimateMode.OFF}

    @property
    def hvac_mode(self) -> ClimateMode | None:
        """Return the current hvac mode."""
        return SMART_THERMOSTAT_TO_HA_HVAC_MODE.get(self.preset_mode, ClimateMode.OFF)

    @property
    def hvac_action(self) -> ClimateAction | None:
        """Return current action."""
        return self.get_action()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.get_current_temperature()

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.get_target_temperature()

    @update_after_operation
    async def set_hvac_mode(self, hvac_mode: ClimateMode) -> None:
        """Set the hvac mode."""
        if hvac_mode == ClimateMode.OFF:
            return await self.turn_off()
        return await self.set_preset_mode("comfort")

    @update_after_operation
    async def set_preset_mode(self, preset_mode: str) -> bool:
        """Send command to set thermostat preset_mode."""
        return await self._send_command(COMMAND_SET_MODE[preset_mode])

    @update_after_operation
    async def set_target_temperature(self, temperature: float) -> bool:
        """Send command to set target temperature."""
        if self.preset_mode != SmartThermostatRadiatorMode.MANUAL.name.lower():
            raise RuntimeError("Can only set temperature in MANUAL mode. Please change mode first.")

        temp_value = int(temperature * 10)
        cmd = COMMAND_SET_TEMP.format(f"{temp_value:04X}")

        _LOGGER.debug("Setting temperature %.1f°C in mode %s → cmd=%s", temperature, self.preset_mode, cmd)
        return await self._send_command(cmd)

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

    def get_action(self) -> ClimateAction:
        """Return current action from cache."""
        if not self.is_on():
            return ClimateAction.OFF
        return ClimateAction.HEATING
