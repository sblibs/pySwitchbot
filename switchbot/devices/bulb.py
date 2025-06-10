from __future__ import annotations

from typing import Any

from ..const import SwitchbotModel
from ..const.const import COMMAND_DEVICE_GET_BASIC_INFO
from ..const.light import BulbColorMode, ColorMode
from .base_light import SwitchbotSequenceBaseLight

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

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (res := await self._get_multi_commands_results(COMMAND_DEVICE_GET_BASIC_INFO[SwitchbotModel.COLOR_BULB])):
            return None
        _version_info, _data = res

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
