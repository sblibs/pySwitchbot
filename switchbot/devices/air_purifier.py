"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
import struct
from typing import Any

from bleak.backends.device import BLEDevice

from ..adv_parsers.air_purifier import get_air_purifier_mode
from ..const import SwitchbotModel
from ..const.air_purifier import AirPurifierMode, AirQualityLevel
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)


COMMAND_HEAD = "570f4c"
COMMAND_TURN_OFF = f"{COMMAND_HEAD}010000"
COMMAND_TURN_ON = f"{COMMAND_HEAD}010100"
COMMAND_SET_MODE = {
    AirPurifierMode.LEVEL_1.name.lower(): f"{COMMAND_HEAD}01010100",
    AirPurifierMode.LEVEL_2.name.lower(): f"{COMMAND_HEAD}01010132",
    AirPurifierMode.LEVEL_3.name.lower(): f"{COMMAND_HEAD}01010164",
    AirPurifierMode.AUTO.name.lower(): f"{COMMAND_HEAD}01010200",
    AirPurifierMode.SLEEP.name.lower(): f"{COMMAND_HEAD}01010300",
    AirPurifierMode.PET.name.lower(): f"{COMMAND_HEAD}01010400",
}
DEVICE_GET_BASIC_SETTINGS_KEY = "570f4d81"


class SwitchbotAirPurifier(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Air Purifier."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.AIR_PURIFIER,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.AIR_PURIFIER,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        _LOGGER.debug("data: %s", _data)
        isOn = bool(_data[2] & 0b10000000)
        version_info = (_data[2] & 0b00110000) >> 4
        _mode = _data[2] & 0b00000111
        isAqiValid = bool(_data[3] & 0b00000100)
        child_lock = bool(_data[3] & 0b00000010)
        _aqi_level = (_data[4] & 0b00000110) >> 1
        aqi_level = AirQualityLevel(_aqi_level).name.lower()
        speed = _data[6] & 0b01111111
        pm25 = struct.unpack("<H", _data[12:14])[0] & 0xFFF
        firmware = _data[15] / 10.0
        mode = get_air_purifier_mode(_mode, speed)

        return {
            "isOn": isOn,
            "version_info": version_info,
            "mode": mode,
            "isAqiValid": isAqiValid,
            "child_lock": child_lock,
            "aqi_level": aqi_level,
            "speed": speed,
            "pm25": pm25,
            "firmware": firmware,
        }

    async def _get_basic_info(self) -> bytes | None:
        """Return basic info of device."""
        _data = await self._send_command(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    @update_after_operation
    async def set_preset_mode(self, preset_mode: str) -> bool:
        """Send command to set air purifier preset_mode."""
        result = await self._send_command(COMMAND_SET_MODE[preset_mode])
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_on(self) -> bool:
        """Turn on the air purifier."""
        result = await self._send_command(COMMAND_TURN_ON)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self) -> bool:
        """Turn off the air purifier."""
        result = await self._send_command(COMMAND_TURN_OFF)
        return self._check_command_result(result, 0, {1})

    def get_current_percentage(self) -> Any:
        """Return cached percentage."""
        return self._get_adv_value("speed")

    def is_on(self) -> bool | None:
        """Return air purifier state from cache."""
        return self._get_adv_value("isOn")

    def get_current_aqi_level(self) -> Any:
        """Return cached aqi level."""
        return self._get_adv_value("aqi_level")

    def get_current_pm25(self) -> Any:
        """Return cached pm25."""
        return self._get_adv_value("pm25")

    def get_current_mode(self) -> Any:
        """Return cached mode."""
        return self._get_adv_value("mode")
