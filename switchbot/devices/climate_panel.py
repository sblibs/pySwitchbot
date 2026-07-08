"""Climate Panel Device."""

from __future__ import annotations

import logging

from ..const import SwitchbotModel
from .device import SwitchbotEncryptedDevice

_LOGGER = logging.getLogger(__name__)


class SwitchbotClimatePanel(SwitchbotEncryptedDevice):
    """Representation of a Switchbot Climate Panel."""

    _model = SwitchbotModel.CLIMATE_PANEL

    def get_current_temperature(self) -> float | None:
        """Return the current temperature in Celsius."""
        return self._get_adv_value("temperature")

    def get_current_humidity(self) -> int | None:
        """Return the current relative humidity in percent."""
        return self._get_adv_value("humidity")

    def is_on(self) -> bool | None:
        """Return true if the panel is powered from AC."""
        return self._get_adv_value("isOn")

    def is_motion_detected(self) -> bool | None:
        """Return true if PIR motion is detected."""
        return self._get_adv_value("motion_detected")

    def is_light(self) -> bool | None:
        """Return true when the ambient light level is bright."""
        return self._get_adv_value("is_light")

    def get_on_button_counter(self) -> int | None:
        """Return the ON button press counter (increments on each press)."""
        return self._get_adv_value("on_button_counter")

    def get_off_button_counter(self) -> int | None:
        """Return the OFF button press counter (increments on each press)."""
        return self._get_adv_value("off_button_counter")

    def get_on_button_mode(self) -> int | None:
        """Return the ON button press mode (0=init,1=click,2=double,3=long)."""
        return self._get_adv_value("on_button_mode")

    def get_off_button_mode(self) -> int | None:
        """Return the OFF button press mode (0=init,1=click,2=double,3=long)."""
        return self._get_adv_value("off_button_mode")
