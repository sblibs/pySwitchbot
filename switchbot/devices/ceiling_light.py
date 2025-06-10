from __future__ import annotations

from typing import Any

from ..const.light import (
    DEFAULT_COLOR_TEMP,
    CeilingLightColorMode,
    ColorMode,
)
from .base_light import SwitchbotSequenceBaseLight
from .device import update_after_operation

# Private mapping from device-specific color modes to original ColorMode enum
_CEILING_LIGHT_COLOR_MODE_MAP = {
    CeilingLightColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    CeilingLightColorMode.NIGHT: ColorMode.COLOR_TEMP,
    CeilingLightColorMode.MUSIC: ColorMode.EFFECT,
    CeilingLightColorMode.UNKNOWN: ColorMode.OFF,
}
CEILING_LIGHT_CONTROL_HEADER = "570F5401"


class SwitchbotCeilingLight(SwitchbotSequenceBaseLight):
    """Representation of a Switchbot ceiling light."""

    _turn_on_command = f"{CEILING_LIGHT_CONTROL_HEADER}01FF01FFFF"
    _turn_off_command = f"{CEILING_LIGHT_CONTROL_HEADER}02FF01FFFF"
    _set_brightness_command = f"{CEILING_LIGHT_CONTROL_HEADER}01FF01{{}}"
    _set_color_temp_command = f"{CEILING_LIGHT_CONTROL_HEADER}01FF01{{}}"
    _get_basic_info_command = ["5702", "570f5581"]

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
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        hex_brightness = f"{brightness:02X}"
        color_temp = self._state.get("cw", DEFAULT_COLOR_TEMP)
        hex_data = f"{hex_brightness}{color_temp:04X}"
        result = await self._send_command(self._set_brightness_command.format(hex_data))
        return self._check_command_result(result, 0, {1})

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (
            res := await self._get_multi_commands_results(self._get_basic_info_command)
        ):
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
