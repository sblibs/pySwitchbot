"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
import struct
from typing import Any

from bleak.backends.device import BLEDevice

from ..adv_parsers.air_purifier import get_air_purifier_mode
from .base_light import SwitchbotSequenceBaseLight
from ..const import SwitchbotModel
from ..const.air_purifier import AirPurifierMode, AirQualityLevel
from .device import (
    SwitchbotEncryptedDevice,
    update_after_operation,
)
from ..const.light import ColorMode

_LOGGER = logging.getLogger(__name__)


COMMAND_HEAD = "570f4c"
COMMAND_SET_MODE = {
    AirPurifierMode.LEVEL_1.name.lower(): f"{COMMAND_HEAD}01010100",
    AirPurifierMode.LEVEL_2.name.lower(): f"{COMMAND_HEAD}01010132",
    AirPurifierMode.LEVEL_3.name.lower(): f"{COMMAND_HEAD}01010164",
    AirPurifierMode.AUTO.name.lower(): f"{COMMAND_HEAD}01010200",
    AirPurifierMode.SLEEP.name.lower(): f"{COMMAND_HEAD}01010300",
    AirPurifierMode.PET.name.lower(): f"{COMMAND_HEAD}01010400",
}
DEVICE_GET_BASIC_SETTINGS_KEY = "570f4d81"
COMMAND_SET_PERCENTAGE = f"{COMMAND_HEAD}02{{percentage:02x}}"
READ_LED_SETTINGS_COMMAND = "570f4d05"
READ_LED_STATUS_COMMAND = "570f4d07"

class SwitchbotAirPurifier(SwitchbotSequenceBaseLight, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Air Purifier."""

    _turn_on_command = f"{COMMAND_HEAD}010100"
    _turn_off_command = f"{COMMAND_HEAD}010000"
    _open_child_lock_command = f"{COMMAND_HEAD}0301"
    _close_child_lock_command = f"{COMMAND_HEAD}0300"
    _open_wireless_charging_command = f"{COMMAND_HEAD}0d01"
    _close_wireless_charging_command = f"{COMMAND_HEAD}0d00"
    _open_light_sensitive_command = f"{COMMAND_HEAD}0702"
    _turn_led_on_command = f"{COMMAND_HEAD}0701"
    _turn_led_off_command = f"{COMMAND_HEAD}0700" 
    _set_rgb_command = _set_brightness_command = f"{COMMAND_HEAD}0501{{}}"
    _get_basic_info_command = [DEVICE_GET_BASIC_SETTINGS_KEY, READ_LED_SETTINGS_COMMAND, READ_LED_STATUS_COMMAND]

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.AIR_PURIFIER_US,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.AIR_PURIFIER_US,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        return ColorMode.RGB
    
    @property
    def led_state(self) -> bool | None:
        """Return LED state from cache."""
        return self.is_led_on()

    @property
    def is_led_on(self) -> bool | None:
        """Return LED state from cache."""
        return self._get_adv_value("led_status")
    
    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (res := await self._get_basic_info_by_multi_commands(self._get_basic_info_command)):
            return None
        
        _data, led_settings, led_status =  res[0], res[1], res[2]

        _LOGGER.debug("%s %s basic info %s", self._model, self._device.address, _data.hex())
        _LOGGER.debug("%s %s led settings %s", self._model, self._device.address, led_settings.hex())
        _LOGGER.debug("%s %s led_status %s", self._model, self._device.address, led_status.hex())
        isOn = bool(_data[2] & 0b10000000)
        wireless_charging = bool(_data[2] & 0b01000000)
        version_info = (_data[2] & 0b00110000) >> 4
        _mode = _data[2] & 0b00000111
        isAqiValid = bool(_data[3] & 0b00000100)
        child_lock = bool(_data[3] & 0b00000010)
        _aqi_level = (_data[4] & 0b00000110) >> 1
        aqi_level = AirQualityLevel(_aqi_level).name.lower()
        speed = _data[6] & 0b01111111
        pm25 = struct.unpack(">H", _data[12:14])[0] & 0xFFF
        firmware = _data[15] / 10.0
        mode = get_air_purifier_mode(_mode, speed)
        self._state["r"] = led_settings[2]
        self._state["g"] = led_settings[3]
        self._state["b"] = led_settings[4]
        brightness = led_settings[5]
        light_sensitive = bool(led_status[1] & 0x02)
        led_status = bool(led_status[1] & 0x01)
        
        data = {
            "isOn": isOn,
            "wireless_charging": wireless_charging,
            "version_info": version_info,
            "mode": mode,
            "isAqiValid": isAqiValid,
            "child_lock": child_lock,
            "aqi_level": aqi_level,
            "speed": speed,
            "firmware": firmware,
            "brightness": brightness,
            "light_sensitive": light_sensitive,
            "led_status": led_status,
        }
        if self._model in (SwitchbotModel.AIR_PURIFIER_JP, SwitchbotModel.AIR_PURIFIER_TABLE_JP):
            return data
        return data | {"pm25": pm25}
    
    async def _get_basic_info(self) -> bytes | None:
        """Return basic info of device."""
        _data = await self._send_command(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data
    
    async def read_led_settings(self) -> dict[str, Any] | None:
        """Read LED settings."""
        if not (_data := await self._send_command()):
            return None

        led_brightness = (_data[2] & 0b00001100) >> 2
        led_color = _data[2] & 0b00000011
        return {"led_brightness": led_brightness, "led_color": led_color}

    @update_after_operation
    async def set_preset_mode(self, preset_mode: str) -> bool:
        """Send command to set air purifier preset_mode."""
        result = await self._send_command(COMMAND_SET_MODE[preset_mode])
        return self._check_command_result(result, 0, {1})
    
    @update_after_operation
    async def set_percentage(self, percentage: int) -> bool:
        """Set percentage."""
        assert 0 <= percentage <= 100, "Percentage must be between 0 and 100"
        self._validate_current_mode()
        
        result = await self._send_command(COMMAND_SET_PERCENTAGE.format(percentage=percentage))
        return self._check_command_result(result, 0, {1})
    
    def _validate_current_mode(self) -> None:
        """Validate current mode for setting percentage."""
        current_mode = self.get_current_mode()
        if current_mode not in (AirPurifierMode.LEVEL_1.name.lower(), AirPurifierMode.LEVEL_2.name.lower(), AirPurifierMode.LEVEL_3.name.lower()):
            raise ValueError("Percentage can only be set in LEVEL modes.")

    @update_after_operation
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        r, g, b = self._state.get("r", 0), self._state.get("g", 0), self._state.get("b", 0)
        hex_data = f"{r:02X}{g:02X}{b:02X}{brightness:02X}"
        result = await self._send_command(
            self._set_brightness_command.format(hex_data)
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 0 <= r <= 255, "r must be between 0 and 255"
        assert 0 <= g <= 255, "g must be between 0 and 255"
        assert 0 <= b <= 255, "b must be between 0 and 255"
        hex_data = f"{r:02X}{g:02X}{b:02X}{brightness:02X}"
        result = await self._send_command(self._set_rgb_command.format(hex_data))
        return self._check_command_result(result, 0, {1})
    
    @update_after_operation
    async def turn_led_on(self) -> bool:
        """Turn on LED."""
        result = await self._send_command(self._turn_led_on_command)
        return self._check_command_result(result, 0, {1})
    
    @update_after_operation
    async def turn_led_off(self) -> bool:
        """Turn off LED."""
        result = await self._send_command(self._turn_led_off_command)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def open_light_sensitive(self) -> bool:
        """Open the light sensitive."""
        result = await self._send_command(self._open_light_sensitive_command)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def close_light_sensitive(self) -> bool:
        """Close the light sensitive."""
        if self.is_led_on():
            result = await self._send_command(self._turn_led_on_command)
        else:
            result = await self._send_command(self._turn_led_off_command)    
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
    
    def is_child_lock_on(self) -> bool | None:
        """Return child lock state from cache."""
        return self._get_adv_value("child_lock")
    
    def is_wireless_charging_on(self) -> bool | None:
        """Return wireless charging state from cache."""
        return self._get_adv_value("wireless_charging")
    
    def get_current_percentage(self) -> int | None:
        """Return cached percentage."""
        return self._get_adv_value("speed")

    def is_light_sensitive_on(self) -> bool | None:
        """Return light sensitive state from cache."""
        return self._get_adv_value("light_sensitive")