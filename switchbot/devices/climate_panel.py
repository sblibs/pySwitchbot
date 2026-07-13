"""Device handler for the Climate Panel."""

from __future__ import annotations

import logging

from ..const import SwitchbotModel
from .device import SwitchbotEncryptedDevice

_LOGGER = logging.getLogger(__name__)


class SwitchbotClimatePanel(SwitchbotEncryptedDevice):
    """Representation of a Switchbot Climate Panel."""

    _model = SwitchbotModel.CLIMATE_PANEL

    def get_current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._get_adv_value("temperature")

    def get_current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._get_adv_value("humidity")

    def is_on(self) -> bool | None:
        """Return whether the panel is on."""
        return self._get_adv_value("isOn")

    def is_motion_detected(self) -> bool | None:
        """Return whether motion is detected."""
        return self._get_adv_value("motion_detected")

    def is_light(self) -> bool | None:
        """Return whether the ambient light is bright."""
        return self._get_adv_value("is_light")

    def get_on_keystate(self) -> int | None:
        """Return the raw ON button keystate byte (mode << 5 | counter)."""
        return self._get_adv_value("on_keystate")

    def get_off_keystate(self) -> int | None:
        """Return the raw OFF button keystate byte (mode << 5 | counter)."""
        return self._get_adv_value("off_keystate")

    def get_on_keystate_mode(self) -> int | None:
        """Return the ON button press mode (0: init, 1: single, 2: double, 3: long)."""
        return self._get_adv_value("on_keystate_mode")

    def get_on_keystate_counter(self) -> int | None:
        """Return the ON button press counter (0: init, 1-30 cyclic)."""
        return self._get_adv_value("on_keystate_counter")

    def get_off_keystate_mode(self) -> int | None:
        """Return the OFF button press mode (0: init, 1: single, 2: double, 3: long)."""
        return self._get_adv_value("off_keystate_mode")

    def get_off_keystate_counter(self) -> int | None:
        """Return the OFF button press counter (0: init, 1-30 cyclic)."""
        return self._get_adv_value("off_keystate_counter")
