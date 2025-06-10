from __future__ import annotations

from typing import Any

from ..const import SwitchbotModel
from ..const.const import COMMAND_DEVICE_GET_BASIC_INFO
from ..const.light import (
    CeilingLightColorMode,
    ColorMode,
)
from .base_light import SwitchbotSequenceBaseLight

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
    def color_modes(self) -> set[CeilingLightColorMode]:
        """Return the supported color modes."""
        return {CeilingLightColorMode.COLOR_TEMP}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = CeilingLightColorMode(self._get_adv_value("color_mode") or 10)
        return _CEILING_LIGHT_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (res := await self._get_multi_commands_results(COMMAND_DEVICE_GET_BASIC_INFO[SwitchbotModel.CEILING_LIGHT])):
            return None
        _version_info, _data = res

        self._state["cw"] = int.from_bytes(_data[3:5], "big")

        return {
            "isOn": bool(_data[1] & 0b10000000),
            "color_mode": _data[1] & 0b01000000,
            "brightness": _data[2] & 0b01111111,
            "cw": self._state["cw"],
            "firmware": _version_info[2] / 10.0,
        }
