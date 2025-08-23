from __future__ import annotations

from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.light import ColorMode, RGBICStripLightColorMode, StripLightColorMode
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
_RGBICWW_STRIP_LIGHT_COLOR_MODE_MAP = {
    RGBICStripLightColorMode.SEGMENTED: ColorMode.EFFECT,
    RGBICStripLightColorMode.RGB: ColorMode.RGB,
    RGBICStripLightColorMode.SCENE: ColorMode.EFFECT,
    RGBICStripLightColorMode.MUSIC: ColorMode.EFFECT,
    RGBICStripLightColorMode.CONTROLLER: ColorMode.EFFECT,
    RGBICStripLightColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    RGBICStripLightColorMode.UNKNOWN: ColorMode.OFF,
}
LIGHT_STRIP_CONTROL_HEADER = "570F4901"
COMMON_EFFECTS = {
    "christmas": [
        "570F49070200033C01",
        "570F490701000600009902006D0EFF0021",
        "570F490701000603009902006D0EFF0021",
    ],
    "halloween": ["570F49070200053C04", "570F490701000300FF6A009E00ED00EA0F"],
    "sunset": [
        "570F49070200033C3C",
        "570F490701000900FF9000ED8C04DD5800",
        "570F490701000903FF2E008E0B004F0500",
        "570F4907010009063F0010270056140033",
    ],
    "vitality": [
        "570F49070200053C02",
        "570F490701000600C5003FD9530AEC9800",
        "570F490701000603FFDF0000895500468B",
    ],
    "flashing": [
        "570F49070200053C02",
        "570F4907010006000000FF00FF00FF0000",
        "570F490701000603FFFF0000FFFFA020F0",
    ],
    "strobe": ["570F49070200043C02", "570F490701000300FF00E19D70FFFF0515"],
    "fade": [
        "570F49070200043C04",
        "570F490701000500FF5481FF00E19D70FF",
        "570F490701000503FF0515FF7FEB",
    ],
    "smooth": [
        "570F49070200033C02",
        "570F4907010007000036FC00F6FF00ED13",
        "570F490701000703F6FF00FF8300FF0800",
        "570F490701000706FF00E1",
    ],
    "forest": [
        "570F49070200033C06",
        "570F490701000400006400228B223CB371",
        "570F49070100040390EE90",
    ],
    "ocean": [
        "570F49070200033C06",
        "570F4907010007004400FF0061FF007BFF",
        "570F490701000703009DFF00B2FF00CBFF",
        "570F49070100070600E9FF",
    ],
    "autumn": [
        "570F49070200043C05",
        "570F490701000700D10035922D13A16501",
        "570F490701000703AB9100DD8C00F4AA29",
        "570F490701000706E8D000",
    ],
    "cool": [
        "570F49070200043C04",
        "570F490701000600001A63006C9A00468B",
        "570F490701000603009DA50089BE4378B6",
    ],
    "flow": [
        "570F49070200033C02",
        "570F490701000600FF00D8E100FFAA00FF",
        "570F4907010006037F00FF5000FF1900FF",
    ],
    "relax": [
        "570F49070200033C03",
        "570F490701000400FF8C00FF7200FF1D00",
        "570F490701000403FF5500",
    ],
    "modern": [
        "570F49070200043C03",
        "570F49070100060089231A5F8969829E5A",
        "570F490701000603BCB05EEDBE5AFF9D60",
    ],
    "rose": [
        "570F49070200043C04",
        "570F490701000500FF1969BC215F7C0225",
        "570F490701000503600C2B35040C",
    ],
}
RGBIC_EFFECTS = {
    "romance": [
        "570F490D01350100FF10EE",
        "570F490D0363",
    ],
    "energy": [
        "570F490D01000300ED070F34FF14FFE114",
        "570F490D03FA",
    ],
    "heartbeat": [
        "570F490D01020400FFDEADFE90FDFF9E3D",
        "570F490D01020403FCBAFD",
        "570F490D03FA",
    ],
    "party": [
        "570F490D01030400FF8A47FF524DFF4DEE",
        "570F490D010304034DFF8C",
        "570F490D03FA",
    ],
    "dynamic": [
        "570F490D010403004DFFFB4DFF4FFFBF4D",
        "570F490D03FA",
    ],
    "mystery": [
        "570F490D01050300F660F6F6D460C6F660",
        "570F490D03FA",
    ],
    "lightning": [
        "570F490D01340100FFD700",
        "570F490D03FA",
    ],
    "rock": [
        "570F490D01090300B0F6606864FCFFBC3D",
        "570F490D03FA",
    ],
    "starlight": [
        "570F490D010A0100FF8C00",
        "570F490D0363",
    ],
    "valentine_day": [
        "570F490D010C0300FDE0FFFFCC8AD7FF8A",
        "570F490D03FA",
    ],
    "dream": [
        "570F490D010E0300A3E5FF73F019FFA8E5",
        "570F490D03FA",
    ],
    "alarm": [
        "570F490D013E0100FF0000",
        "570F490D03FA",
    ],
    "fireworks": [
        "570F490D01110300FFAA33FFE233FF5CDF",
        "570F490D03FA",
    ],
    "waves": [
        "570F490D013D01001E90FF",
        "570F490D03FA",
    ],
    "christmas": [
        "570F490D01380400DC143C228B22DAA520",
        "570F490D0363",
        "570F490D0138040332CD32",
        "570F490D0363",
    ],
    "rainbow": [
        "570F490D01160600FF0000FF7F00FFFF00",
        "570F490D03FA",
        "570F490D0116060300FF000000FF9400D3",
        "570F490D03FA",
    ],
    "game": [
        "570F490D011A0400D05CFF668FFFFFEFD5",
        "570F490D0363",
        "570F490D011A0403FFC55C",
        "570F490D0363",
    ],
    "halloween": [
        "570F490D01320300FF8C009370DB32CD32",
        "570F490D0364",
    ],
    "meditation": [
        "570F490D013502001E90FF9370DB",
        "570F490D0364",
    ],
    "starlit_sky": [
        "570F490D010D010099C8FF",
        "570F490D0364",
    ],
    "sleep": [
        "570F490D01370300FF8C002E4E3E3E3E5E",
        "570F490D0364",
    ],
    "movie": [
        "570F490D013602001919704B0082",
        "570F490D0364",
    ],
    "sunrise": [
        "570F490D013F0200FFD700FF4500",
        "570F490D03FA",
        "570F490D03FA",
    ],
    "sunset": [
        "570F490D01390300FF4500FFA500483D8B",
        "570F490D0363",
        "570F490D0363",
    ],
    "new_year": [
        "570F490D013F0300FF0000FFD700228B22",
        "570F490D0364",
    ],
    "cherry_blossom": [
        "570F490D01400200FFB3C1FF69B4",
        "570F490D0364",
    ],
}


class SwitchbotLightStrip(SwitchbotSequenceBaseLight):
    """Representation of a Switchbot light strip."""

    _effect_dict = COMMON_EFFECTS
    _turn_on_command = f"{LIGHT_STRIP_CONTROL_HEADER}01"
    _turn_off_command = f"{LIGHT_STRIP_CONTROL_HEADER}02"
    _set_rgb_command = f"{LIGHT_STRIP_CONTROL_HEADER}12{{}}"
    _set_color_temp_command = f"{LIGHT_STRIP_CONTROL_HEADER}11{{}}"
    _set_brightness_command = f"{LIGHT_STRIP_CONTROL_HEADER}14{{}}"
    _get_basic_info_command = ["570003", "570f4A01"]

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = StripLightColorMode(self._get_adv_value("color_mode") or 10)
        return _STRIP_LIGHT_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (
            res := await self._get_multi_commands_results(self._get_basic_info_command)
        ):
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


class SwitchbotRgbicLight(SwitchbotEncryptedDevice, SwitchbotLightStrip):
    """Support for Switchbot RGBIC lights."""

    _effect_dict = RGBIC_EFFECTS

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.RGBICWW_STRIP_LIGHT,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.RGBICWW_STRIP_LIGHT,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB, ColorMode.COLOR_TEMP}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        device_mode = RGBICStripLightColorMode(self._get_adv_value("color_mode") or 10)
        return _RGBICWW_STRIP_LIGHT_COLOR_MODE_MAP.get(device_mode, ColorMode.OFF)
