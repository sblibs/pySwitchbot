"""Device handler for the Modern Ceiling Fan."""

from typing import Any, ClassVar

from ..const import SwitchbotModel
from ..const.fan import CirculatorFanProMode
from .device import update_after_operation
from .fan import SwitchbotCirculatorFanPro


class SwitchbotModernCeilingFan(SwitchbotCirculatorFanPro):
    """Control a W1071 fan and its independent light channels."""

    _model = SwitchbotModel.MODERN_CEILING_FAN
    _command_set_mode: ClassVar[dict[str, str]] = {
        **{
            mode.name.lower(): f"570f41112901{mode.value:02X}"
            for mode in CirculatorFanProMode
        },
        "reverse": "570f4111290106",
    }

    _command_start_oscillation: ClassVar[str] = "570f4102010101"
    _command_stop_oscillation: ClassVar[str] = "570f4102010202"
    _command_start_horizontal_oscillation: ClassVar[str] = "570f41020101ff"
    _command_stop_horizontal_oscillation: ClassVar[str] = "570f41020102ff"
    _command_start_vertical_oscillation: ClassVar[str] = "570f410201ff01"
    _command_stop_vertical_oscillation: ClassVar[str] = "570f410201ff02"

    @property
    def fan_modes(self) -> list[str]:
        return [*super().fan_modes, "reverse"]

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Read firmware and RGB values without overwriting advertised state."""
        info = await super().get_basic_info()
        data = await self._send_command("570f978101")
        if not data or len(data) < 17 or data[0] != 1:
            return info
        return (info or {}) | {"color_light_rgb": tuple(data[7:10])}

    @update_after_operation
    async def set_percentage(self, percentage: int) -> bool:
        """Set speed while preserving reverse mode."""
        percentage = max(1, min(100, percentage))
        mode = 6 if self.get_current_mode() == "reverse" else 1
        result = await self._send_command(f"570f41112901{mode:02X}{percentage:02X}")
        return self._check_command_result(result, 0, {1})

    @property
    def main_light_is_on(self) -> bool | None:
        return self._get_adv_value("main_light_is_on")

    @property
    def main_light_brightness(self) -> int | None:
        return self._get_adv_value("main_light_brightness")

    @property
    def main_light_color_temp(self) -> int | None:
        return self._get_adv_value("main_light_color_temp")

    @property
    def color_light_is_on(self) -> bool | None:
        return self._get_adv_value("color_light_is_on")

    @property
    def color_light_brightness(self) -> int | None:
        return self._get_adv_value("color_light_brightness")

    @property
    def color_light_rgb(self) -> tuple[int, int, int] | None:
        return self._get_adv_value("color_light_rgb")

    @update_after_operation
    async def set_main_light(
        self, is_on: bool, brightness: int | None = None, color_temp: int | None = None
    ) -> bool:
        """Set white-light state without changing RGB or fan power."""
        if brightness is not None and not 1 <= brightness <= 100:
            raise ValueError("Brightness must be between 1 and 100")
        if color_temp is not None and not 2700 <= color_temp <= 6500:
            raise ValueError("Color temperature must be between 2700 and 6500")
        selector = "81" if is_on else "82"
        result = await self._send_command("570f49112901" + selector)
        if not self._check_command_result(result, 0, {1}):
            return False
        if not is_on or (brightness is None and color_temp is None):
            return True
        if brightness is not None and color_temp is not None:
            payload = f"11{brightness:02X}{color_temp:04X}"
        elif brightness is not None:
            payload = f"09{brightness:02X}"
        else:
            payload = f"10{color_temp:04X}"
        result = await self._send_command("570f491129" + payload)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_color_light(
        self,
        is_on: bool,
        brightness: int | None = None,
        rgb: tuple[int, int, int] | None = None,
    ) -> bool:
        """Set RGB-light state without changing white or fan power."""
        if brightness is not None and not 1 <= brightness <= 100:
            raise ValueError("Brightness must be between 1 and 100")
        if rgb is not None and (
            len(rgb) != 3 or any(not 0 <= channel <= 255 for channel in rgb)
        ):
            raise ValueError("RGB channels must be between 0 and 255")
        if rgb is not None and brightness is None:
            brightness = self.color_light_brightness or 100
        selector = "84" if is_on else "88"
        result = await self._send_command("570f49112901" + selector)
        if not self._check_command_result(result, 0, {1}):
            return False
        if not is_on or (brightness is None and rgb is None):
            return True
        if rgb is not None:
            payload = f"12{brightness:02X}" + bytes(rgb).hex() + "00ff"
        else:
            payload = f"14{brightness:02X}"
        result = await self._send_command("570f491129" + payload)
        return self._check_command_result(result, 0, {1})
