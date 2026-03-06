"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
from typing import Any

from ..const.fan import FanMode, StandingFanMode
from .device import (
    DEVICE_GET_BASIC_SETTINGS_KEY,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)


COMMAND_HEAD = "570f41"
COMMAND_START_OSCILLATION = f"{COMMAND_HEAD}02010101"  # H+V start
COMMAND_STOP_OSCILLATION = f"{COMMAND_HEAD}02010202"  # H+V stop
COMMAND_START_HORIZONTAL_OSCILLATION = f"{COMMAND_HEAD}020101ff"  # H start, V keep
COMMAND_STOP_HORIZONTAL_OSCILLATION = f"{COMMAND_HEAD}020102ff"  # H stop, V keep
COMMAND_START_VERTICAL_OSCILLATION = f"{COMMAND_HEAD}0201ff01"  # H keep, V start
COMMAND_STOP_VERTICAL_OSCILLATION = f"{COMMAND_HEAD}0201ff02"  # H keep, V stop
COMMAND_SET_MODE = {
    FanMode.NORMAL.name.lower(): f"{COMMAND_HEAD}030101ff",
    FanMode.NATURAL.name.lower(): f"{COMMAND_HEAD}030102ff",
    FanMode.SLEEP.name.lower(): f"{COMMAND_HEAD}030103",
    FanMode.BABY.name.lower(): f"{COMMAND_HEAD}030104",
}
COMMAND_SET_PERCENTAGE = f"{COMMAND_HEAD}0302"  #  +speed
COMMAND_GET_BASIC_INFO = "570f428102"


class SwitchbotFan(SwitchbotSequenceDevice):
    """Representation of a Switchbot Circulator Fan."""

    _turn_on_command = f"{COMMAND_HEAD}0101"
    _turn_off_command = f"{COMMAND_HEAD}0102"

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (_data1 := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None

        _LOGGER.debug("data: %s", _data)
        battery = _data[2] & 0b01111111
        isOn = bool(_data[3] & 0b10000000)
        oscillating_horizontal = bool(_data[3] & 0b01000000)
        oscillating_vertical = bool(_data[3] & 0b00100000)
        oscillating = oscillating_horizontal or oscillating_vertical
        _mode = _data[8] & 0b00000111
        mode = FanMode(_mode).name.lower() if 1 <= _mode <= 4 else None
        speed = _data[9]
        firmware = _data1[2] / 10.0

        return {
            "battery": battery,
            "isOn": isOn,
            "oscillating": oscillating,
            "oscillating_horizontal": oscillating_horizontal,
            "oscillating_vertical": oscillating_vertical,
            "mode": mode,
            "speed": speed,
            "firmware": firmware,
        }

    async def _get_basic_info(self, cmd: str) -> bytes | None:
        """Return basic info of device."""
        _data = await self._send_command(key=cmd, retry=self._retry_count)

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    @update_after_operation
    async def set_preset_mode(self, preset_mode: str) -> bool:
        """Send command to set fan preset_mode."""
        return await self._send_command(COMMAND_SET_MODE[preset_mode])

    @update_after_operation
    async def set_percentage(self, percentage: int) -> bool:
        """Send command to set fan percentage."""
        return await self._send_command(f"{COMMAND_SET_PERCENTAGE}{percentage:02X}")

    @update_after_operation
    async def set_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan oscillation"""
        if oscillating:
            return await self._send_command(COMMAND_START_OSCILLATION)
        return await self._send_command(COMMAND_STOP_OSCILLATION)

    @update_after_operation
    async def set_horizontal_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan horizontal (left-right) oscillation only."""
        if oscillating:
            return await self._send_command(COMMAND_START_HORIZONTAL_OSCILLATION)
        return await self._send_command(COMMAND_STOP_HORIZONTAL_OSCILLATION)

    @update_after_operation
    async def set_vertical_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan vertical (up-down) oscillation only."""
        if oscillating:
            return await self._send_command(COMMAND_START_VERTICAL_OSCILLATION)
        return await self._send_command(COMMAND_STOP_VERTICAL_OSCILLATION)

    def get_current_percentage(self) -> Any:
        """Return cached percentage."""
        return self._get_adv_value("speed")

    def is_on(self) -> bool | None:
        """Return fan state from cache."""
        return self._get_adv_value("isOn")

    def get_oscillating_state(self) -> Any:
        """Return cached oscillating."""
        return self._get_adv_value("oscillating")

    def get_horizontal_oscillating_state(self) -> Any:
        """Return cached horizontal (left-right) oscillating state."""
        return self._get_adv_value("oscillating_horizontal")

    def get_vertical_oscillating_state(self) -> Any:
        """Return cached vertical (up-down) oscillating state."""
        return self._get_adv_value("oscillating_vertical")

    def get_current_mode(self) -> Any:
        """Return cached mode."""
        return self._get_adv_value("mode")


class SwitchbotStandingFan(SwitchbotFan):
    """Representation of a Switchbot Standing Fan."""

    COMMAND_SET_MODE = {
        StandingFanMode.NORMAL.name.lower(): f"{COMMAND_HEAD}030101ff",
        StandingFanMode.NATURAL.name.lower(): f"{COMMAND_HEAD}030102ff",
        StandingFanMode.SLEEP.name.lower(): f"{COMMAND_HEAD}030103",
        StandingFanMode.BABY.name.lower(): f"{COMMAND_HEAD}030104",
        StandingFanMode.CUSTOM_NATURAL.name.lower(): f"{COMMAND_HEAD}030105",
    }
    COMMAND_SET_OSCILLATION_PARAMS = f"{COMMAND_HEAD}0202"
    COMMAND_SET_NIGHT_LIGHT = f"{COMMAND_HEAD}0502"

    @update_after_operation
    async def set_preset_mode(self, preset_mode: str) -> bool:
        """Send command to set fan preset_mode."""
        return await self._send_command(self.COMMAND_SET_MODE[preset_mode])

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (_data1 := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None

        _LOGGER.debug("data: %s", _data)
        battery = _data[2] & 0b01111111
        isOn = bool(_data[3] & 0b10000000)
        oscillating_horizontal = bool(_data[3] & 0b01000000)
        oscillating_vertical = bool(_data[3] & 0b00100000)
        oscillating = oscillating_horizontal or oscillating_vertical
        _mode = _data[8] & 0b00000111
        mode = StandingFanMode(_mode).name.lower() if 1 <= _mode <= 5 else None
        speed = _data[9]
        firmware = _data1[2] / 10.0

        return {
            "battery": battery,
            "isOn": isOn,
            "oscillating": oscillating,
            "oscillating_horizontal": oscillating_horizontal,
            "oscillating_vertical": oscillating_vertical,
            "mode": mode,
            "speed": speed,
            "firmware": firmware,
        }

    @update_after_operation
    async def set_horizontal_oscillation_angle(self, angle: int) -> bool:
        """Set horizontal oscillation angle (30/60/90)."""
        cmd = f"{self.COMMAND_SET_OSCILLATION_PARAMS}{angle:02X}FFFFFF"
        return await self._send_command(cmd)

    @update_after_operation
    async def set_vertical_oscillation_angle(self, angle: int) -> bool:
        """Set vertical oscillation angle (30/60/90)."""
        cmd = f"{self.COMMAND_SET_OSCILLATION_PARAMS}FFFF{angle:02X}FF"
        return await self._send_command(cmd)

    @update_after_operation
    async def set_night_light(self, state: int) -> bool:
        """Set night light state. 1=level1, 2=level2, 3=off."""
        cmd = f"{self.COMMAND_SET_NIGHT_LIGHT}{state:02X}FFFF"
        return await self._send_command(cmd)

    def get_night_light_state(self) -> int | None:
        """Return cached night light state."""
        return self._get_adv_value("nightLight")
