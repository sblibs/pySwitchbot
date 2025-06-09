from __future__ import annotations

import logging
from typing import Any

from ..const.light import BulbColorMode, ColorMode
from .base_light import SwitchbotSequenceBaseLight
from .device import REQ_HEADER, SwitchbotOperationError, update_after_operation

BULB_COMMAND_HEADER = "4701"
BULB_REQUEST = f"{REQ_HEADER}4801"

BULB_COMMAND = f"{REQ_HEADER}{BULB_COMMAND_HEADER}"
# Bulb keys
BULB_ON_KEY = f"{BULB_COMMAND}01"
BULB_OFF_KEY = f"{BULB_COMMAND}02"
RGB_BRIGHTNESS_KEY = f"{BULB_COMMAND}12"
CW_BRIGHTNESS_KEY = f"{BULB_COMMAND}13"
BRIGHTNESS_KEY = f"{BULB_COMMAND}14"
RGB_KEY = f"{BULB_COMMAND}16"
CW_KEY = f"{BULB_COMMAND}17"

DEVICE_GET_VERSION_KEY = "570003"
DEVICE_GET_BASIC_SETTINGS_KEY = "570f4801"

_LOGGER = logging.getLogger(__name__)


EFFECT_DICT = {
    "Colorful": "570F4701010300",
    "Flickering": "570F4701010301",
    "Breathing": "570F4701010302",
}

# Private mapping from device-specific color modes to original ColorMode enum
_BULB_COLOR_MODE_MAP = {
    BulbColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    BulbColorMode.RGB: ColorMode.RGB,
    BulbColorMode.DYNAMIC: ColorMode.EFFECT,
    BulbColorMode.UNKNOWN: ColorMode.OFF,
}


class SwitchbotBulb(SwitchbotSequenceBaseLight):
    """Representation of a Switchbot bulb."""

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB, ColorMode.COLOR_TEMP}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = BulbColorMode(self._get_adv_value("color_mode") or 10)
        return _BULB_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)

    @property
    def get_effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return list(EFFECT_DICT.keys())

    @update_after_operation
    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(BULB_ON_KEY)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(BULB_OFF_KEY)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        result = await self._send_command(f"{BRIGHTNESS_KEY}{brightness:02X}")
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 2700 <= color_temp <= 6500, "Color Temp must be between 2700 and 6500"
        result = await self._send_command(
            f"{CW_BRIGHTNESS_KEY}{brightness:02X}{color_temp:04X}"
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 0 <= r <= 255, "r must be between 0 and 255"
        assert 0 <= g <= 255, "g must be between 0 and 255"
        assert 0 <= b <= 255, "b must be between 0 and 255"
        result = await self._send_command(
            f"{RGB_BRIGHTNESS_KEY}{brightness:02X}{r:02X}{g:02X}{b:02X}"
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_effect(self, effect: str) -> bool:
        """Set effect."""
        effect_template = EFFECT_DICT.get(effect)
        if not effect_template:
            raise SwitchbotOperationError(f"Effect {effect} not supported")
        result = await self._send_command(effect_template)
        if result:
            self._override_state({"effect": effect})
        return result

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None
        if not (_version_info := await self._get_basic_info(DEVICE_GET_VERSION_KEY)):
            return None

        _LOGGER.debug(
            "data: %s, version info: %s, address: %s",
            _data,
            _version_info,
            self._device.address,
        )

        self._state["r"] = _data[3]
        self._state["g"] = _data[4]
        self._state["b"] = _data[5]
        self._state["cw"] = int.from_bytes(_data[6:8], "big")

        return {
            "isOn": bool(_data[1] & 0b10000000),
            "brightness": _data[2] & 0b01111111,
            "r": self._state["r"],
            "g": self._state["g"],
            "b": self._state["b"],
            "cw": self._state["cw"],
            "color_mode": _data[10] & 0b00001111,
            "firmware": _version_info[2] / 10.0,
        }
