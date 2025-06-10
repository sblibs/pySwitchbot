from __future__ import annotations

from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.const import COMMAND_DEVICE_GET_BASIC_INFO
from ..const.light import ColorMode, StripLightColorMode
from .base_light import SwitchbotSequenceBaseLight
from .device import SwitchbotEncryptedDevice

# Private mapping from device-specific color modes to original ColorMode enum
_STRIP_LIGHT_COLOR_MODE_MAP = {
    StripLightColorMode.RGB: ColorMode.RGB,
    StripLightColorMode.SCENE: ColorMode.EFFECT,
    StripLightColorMode.MUSIC: ColorMode.EFFECT,
    StripLightColorMode.CONTROLLER: ColorMode.EFFECT,
    StripLightColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    StripLightColorMode.UNKNOWN: ColorMode.OFF,
}


class SwitchbotLightStrip(SwitchbotSequenceBaseLight):
    """Representation of a Switchbot light strip."""

    @property
    def color_modes(self) -> set[StripLightColorMode]:
        """Return the supported color modes."""
        return {StripLightColorMode.RGB}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = StripLightColorMode(self._get_adv_value("color_mode") or 10)
        return _STRIP_LIGHT_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (res := await self._get_multi_commands_results(COMMAND_DEVICE_GET_BASIC_INFO[SwitchbotModel.LIGHT_STRIP])):
            return None

        _version_info, _data = res
        self._state["r"] = _data[3]
        self._state["g"] = _data[4]
        self._state["b"] = _data[5]
        self._state["cw"] = int.from_bytes(_data[7:9], "big")

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

class SwitchbotStripLight3(SwitchbotEncryptedDevice, SwitchbotLightStrip):
    """Support for switchbot strip light3 and floor lamp."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.STRIP_LIGHT_3,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.STRIP_LIGHT_3,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB, ColorMode.COLOR_TEMP}

