from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from ..helpers import create_background_task
from ..models import SwitchBotAdvertisement
from .device import SwitchbotDevice

_LOGGER = logging.getLogger(__name__)


class SwitchbotBaseLight(SwitchbotDevice):
    """Representation of a Switchbot light."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot bulb constructor."""
        super().__init__(*args, **kwargs)
        self._state: dict[str, Any] = {}

    @property
    def on(self) -> bool | None:
        """Return if bulb is on."""
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
        return None

    def is_on(self) -> bool | None:
        """Return bulb state from cache."""
        return self._get_adv_value("isOn")

    def get_effect(self):
        """Return the current effect."""
        return self._get_adv_value("effect")

    @abstractmethod
    async def turn_on(self) -> bool:
        """Turn device on."""

    @abstractmethod
    async def turn_off(self) -> bool:
        """Turn device off."""

    @abstractmethod
    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""

    @abstractmethod
    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""

    @abstractmethod
    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""

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
