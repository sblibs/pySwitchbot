from __future__ import annotations

import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.light import ColorMode, StripLightColorMode
from .base_light import SwitchbotSequenceBaseLight
from .device import (
    REQ_HEADER,
    SwitchbotEncryptedDevice,
    SwitchbotOperationError,
    update_after_operation,
)

STRIP_COMMMAND_HEADER = "4901"
STRIP_REQUEST = f"{REQ_HEADER}4A01"

STRIP_COMMAND = f"{REQ_HEADER}{STRIP_COMMMAND_HEADER}"
# Strip keys
STRIP_ON_KEY = f"{STRIP_COMMAND}01"
STRIP_OFF_KEY = f"{STRIP_COMMAND}02"
COLOR_TEMP_KEY = f"{STRIP_COMMAND}11"
RGB_BRIGHTNESS_KEY = f"{STRIP_COMMAND}12"
BRIGHTNESS_KEY = f"{STRIP_COMMAND}14"

DEVICE_GET_VERSION_KEY = "570003"

_LOGGER = logging.getLogger(__name__)

EFFECT_DICT = {
    "Christmas": [
        "570F49070200033C01",
        "570F490701000600009902006D0EFF0021",
        "570F490701000603009902006D0EFF0021",
    ],
    "Halloween": ["570F49070200053C04", "570F490701000300FF6A009E00ED00EA0F"],
    "Sunset": [
        "570F49070200033C3C",
        "570F490701000900FF9000ED8C04DD5800",
        "570F490701000903FF2E008E0B004F0500",
        "570F4907010009063F0010270056140033",
    ],
    "Vitality": [
        "570F49070200053C02",
        "570F490701000600C5003FD9530AEC9800",
        "570F490701000603FFDF0000895500468B",
    ],
    "Flashing": [
        "570F49070200053C02",
        "570F4907010006000000FF00FF00FF0000",
        "570F490701000603FFFF0000FFFFA020F0",
    ],
    "Strobe": ["570F49070200043C02", "570F490701000300FF00E19D70FFFF0515"],
    "Fade": [
        "570F49070200043C04",
        "570F490701000500FF5481FF00E19D70FF",
        "570F490701000503FF0515FF7FEB",
    ],
    "Smooth": [
        "570F49070200033C02",
        "570F4907010007000036FC00F6FF00ED13",
        "570F490701000703F6FF00FF8300FF0800",
        "570F490701000706FF00E1",
    ],
    "Forest": [
        "570F49070200033C06",
        "570F490701000400006400228B223CB371",
        "570F49070100040390EE90",
    ],
    "Ocean": [
        "570F49070200033C06",
        "570F4907010007004400FF0061FF007BFF",
        "570F490701000703009DFF00B2FF00CBFF",
        "570F49070100070600E9FF",
    ],
    "Autumn": [
        "570F49070200043C05",
        "570F490701000700D10035922D13A16501",
        "570F490701000703AB9100DD8C00F4AA29",
        "570F490701000706E8D000",
    ],
    "Cool": [
        "570F49070200043C04",
        "570F490701000600001A63006C9A00468B",
        "570F490701000603009DA50089BE4378B6",
    ],
    "Flow": [
        "570F49070200033C02",
        "570F490701000600FF00D8E100FFAA00FF",
        "570F4907010006037F00FF5000FF1900FF",
    ],
    "Relax": [
        "570F49070200033C03",
        "570F490701000400FF8C00FF7200FF1D00",
        "570F490701000403FF5500",
    ],
    "Modern": [
        "570F49070200043C03",
        "570F49070100060089231A5F8969829E5A",
        "570F490701000603BCB05EEDBE5AFF9D60",
    ],
    "Rose": [
        "570F49070200043C04",
        "570F490701000500FF1969BC215F7C0225",
        "570F490701000503600C2B35040C",
    ],
}

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
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = StripLightColorMode(self._get_adv_value("color_mode") or 10)
        return _STRIP_LIGHT_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)

    @property
    def get_effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return list(EFFECT_DICT.keys())

    @update_after_operation
    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(STRIP_ON_KEY)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(STRIP_OFF_KEY)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        result = await self._send_command(f"{BRIGHTNESS_KEY}{brightness:02X}")
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
        result = await self._send_multiple_commands(effect_template)
        if result:
            self._override_state({"effect": effect})
        return result

    async def get_basic_info(
        self,
        device_get_basic_info: str = STRIP_REQUEST,
        device_get_version_info: str = DEVICE_GET_VERSION_KEY,
    ) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(device_get_basic_info)):
            return None
        if not (_version_info := await self._get_basic_info(device_get_version_info)):
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

    @update_after_operation
    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        assert 0 <= brightness <= 100
        assert self.min_temp <= color_temp <= self.max_temp
        result = await self._send_command(
            f"{COLOR_TEMP_KEY}{brightness:02X}{color_temp:04X}"
        )
        return self._check_command_result(result, 0, {1})
