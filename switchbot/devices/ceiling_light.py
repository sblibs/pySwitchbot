from __future__ import annotations

import logging
from typing import Any

from ..const.light import (
    DEFAULT_COLOR_TEMP,
    CeilingLightColorMode,
    ColorMode,
)
from .base_light import SwitchbotSequenceBaseLight
from .device import REQ_HEADER, update_after_operation

CEILING_LIGHT_COMMAND_HEADER = "5401"
CEILING_LIGHT_REQUEST = f"{REQ_HEADER}5501"

CEILING_LIGHT_COMMAND = f"{REQ_HEADER}{CEILING_LIGHT_COMMAND_HEADER}"
CEILING_LIGHT_ON_KEY = f"{CEILING_LIGHT_COMMAND}01FF01FFFF"
CEILING_LIGHT_OFF_KEY = f"{CEILING_LIGHT_COMMAND}02FF01FFFF"
CW_BRIGHTNESS_KEY = f"{CEILING_LIGHT_COMMAND}010001"
BRIGHTNESS_KEY = f"{CEILING_LIGHT_COMMAND}01FF01"

DEVICE_GET_VERSION_KEY = "5702"
DEVICE_GET_BASIC_SETTINGS_KEY = "570f5581"

_LOGGER = logging.getLogger(__name__)

# Private mapping from device-specific color modes to original ColorMode enum
_CEILING_LIGHT_COLOR_MODE_MAP = {
    CeilingLightColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    CeilingLightColorMode.NIGHT: ColorMode.COLOR_TEMP,
    CeilingLightColorMode.MUSIC: ColorMode.EFFECT,
    CeilingLightColorMode.UNKNOWN: ColorMode.OFF,
}


class SwitchbotCeilingLight(SwitchbotSequenceBaseLight):
    """Representation of a Switchbot ceiling light."""

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.COLOR_TEMP}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = CeilingLightColorMode(self._get_adv_value("color_mode") or 10)
        return _CEILING_LIGHT_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)

    @update_after_operation
    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(CEILING_LIGHT_ON_KEY)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(CEILING_LIGHT_OFF_KEY)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        color_temp = self._state.get("cw", DEFAULT_COLOR_TEMP)
        result = await self._send_command(
            f"{BRIGHTNESS_KEY}{brightness:02X}{color_temp:04X}"
        )
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

        self._state["cw"] = int.from_bytes(_data[3:5], "big")

        return {
            "isOn": bool(_data[1] & 0b10000000),
            "color_mode": _data[1] & 0b01000000,
            "brightness": _data[2] & 0b01111111,
            "cw": self._state["cw"],
            "firmware": _version_info[2] / 10.0,
        }
