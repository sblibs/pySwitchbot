from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from ..helpers import create_background_task
from ..models import SwitchBotAdvertisement
from .device import SwitchbotDevice, SwitchbotOperationError, update_after_operation

_LOGGER = logging.getLogger(__name__)


class SwitchbotBaseLight(SwitchbotDevice):
    """Representation of a Switchbot light."""

    _effect_dict: dict[str, list[str]] = {}
    _set_brightness_command: str = ""
    _set_color_temp_command: str = ""
    _set_rgb_command: str = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot base light constructor."""
        super().__init__(*args, **kwargs)
        self._state: dict[str, Any] = {}

    @property
    def on(self) -> bool | None:
        """Return if light is on."""
        return self.is_on()

    @property
    def rgb(self) -> tuple[int, int, int] | None:
        """Return the current rgb value."""
        if "r" not in self._state or "g" not in self._state or "b" not in self._state:
            return None
        return self._state["r"], self._state["g"], self._state["b"]

    @property
    def color_temp(self) -> int | None:
        """Return the current color temp value."""
        return self._state.get("cw") or self.min_temp

    @property
    def brightness(self) -> int | None:
        """Return the current brightness value."""
        return self._get_adv_value("brightness") or 0

    @property
    @abstractmethod
    def color_mode(self) -> Any:
        """Return the current color mode."""
        raise NotImplementedError("Subclasses must implement color mode")

    @property
    def min_temp(self) -> int:
        """Return minimum color temp."""
        return 2700

    @property
    def max_temp(self) -> int:
        """Return maximum color temp."""
        return 6500

    @property
    def get_effect_list(self) -> list[str] | None:
        """Return the list of supported effects."""
        return list(self._effect_dict) if self._effect_dict else None

    def is_on(self) -> bool | None:
        """Return bulb state from cache."""
        return self._get_adv_value("isOn")

    def get_effect(self):
        """Return the current effect."""
        return self._get_adv_value("effect")

    @update_after_operation
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        hex_brightness = f"{brightness:02X}"
        self._check_function_support(self._set_brightness_command)
        result = await self._send_command(
            self._set_brightness_command.format(hex_brightness)
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 2700 <= color_temp <= 6500, "Color Temp must be between 2700 and 6500"
        hex_data = f"{brightness:02X}{color_temp:04X}"
        self._check_function_support(self._set_color_temp_command)
        result = await self._send_command(self._set_color_temp_command.format(hex_data))
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 0 <= r <= 255, "r must be between 0 and 255"
        assert 0 <= g <= 255, "g must be between 0 and 255"
        assert 0 <= b <= 255, "b must be between 0 and 255"
        self._check_function_support(self._set_rgb_command)
        hex_data = f"{brightness:02X}{r:02X}{g:02X}{b:02X}"
        result = await self._send_command(self._set_rgb_command.format(hex_data))
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_effect(self, effect: str) -> bool:
        """Set effect."""
        effect_template = self._effect_dict.get(effect.lower())
        if not effect_template:
            raise SwitchbotOperationError(f"Effect {effect} not supported")
        result = await self._send_multiple_commands(effect_template)
        if result:
            self._override_state({"effect": effect})
        return result

    async def _send_multiple_commands(self, keys: list[str]) -> bool:
        """
        Send multiple commands to device.

        Since we current have no way to tell which command the device
        needs we send both.
        """
        final_result = False
        for key in keys:
            result = await self._send_command(key)
            final_result |= self._check_command_result(result, 0, {1})
        return final_result

    async def _get_multi_commands_results(
        self, commands: list[str]
    ) -> tuple[bytes, bytes] | None:
        """Check results after sending multiple commands."""
        if not (results := await self._get_basic_info_by_multi_commands(commands)):
            return None

        _version_info, _data = results[0], results[1]
        _LOGGER.debug(
            "version info: %s, data: %s, address: %s",
            _version_info,
            _data,
            self._device.address,
        )
        return _version_info, _data

    async def _get_basic_info_by_multi_commands(
        self, commands: list[str]
    ) -> list[bytes] | None:
        """Get device basic settings by sending multiple commands."""
        results = []
        for command in commands:
            if not (result := await self._get_basic_info(command)):
                return None
            results.append(result)
        return results


class SwitchbotSequenceBaseLight(SwitchbotBaseLight):
    """Representation of a Switchbot light."""

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        current_state = self._get_adv_value("sequence_number")
        super().update_from_advertisement(advertisement)
        new_state = self._get_adv_value("sequence_number")
        _LOGGER.debug(
            "%s: update advertisement: %s (seq before: %s) (seq after: %s)",
            self.name,
            advertisement,
            current_state,
            new_state,
        )
        if current_state != new_state:
            create_background_task(self.update())
