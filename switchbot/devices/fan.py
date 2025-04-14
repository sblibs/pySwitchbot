"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
from typing import Any

from ..const.fan import FanMode
from .device import (
    DEVICE_GET_BASIC_SETTINGS_KEY,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)


COMMAND_HEAD = "570f41"
COMMAND_TURN_ON = f"{COMMAND_HEAD}0101"
COMMAND_TURN_OFF = f"{COMMAND_HEAD}0102"
COMMAND_START_OSCILLATION = f"{COMMAND_HEAD}020101ff"
COMMAND_STOP_OSCILLATION = f"{COMMAND_HEAD}020102ff"
COMMAND_SET_MODE = {
    FanMode.NORMAL.name: f"{COMMAND_HEAD}030101ff",
    FanMode.NATURAL.name: f"{COMMAND_HEAD}030102ff",
    FanMode.SLEEP.name: f"{COMMAND_HEAD}030103",
    FanMode.BABY.name: f"{COMMAND_HEAD}030104",
}
COMMAND_SET_PERCENTAGE = f"{COMMAND_HEAD}0302"  #  +speed
COMMAND_GET_BASIC_INFO = "570f428102"


class SwitchbotFan(SwitchbotSequenceDevice):
    """Representation of a Switchbot Circulator Fan."""

    def __init__(self, device, password=None, interface=0, **kwargs):
        super().__init__(device, password, interface, **kwargs)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (_data1 := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None

        _LOGGER.debug("data: %s", _data)
        battery = _data[2] & 0b01111111
        isOn = bool(_data[3] & 0b10000000)
        oscillating = bool(_data[3] & 0b01100000)
        _mode = _data[8] & 0b00000111
        mode = FanMode(_mode).name if 1 <= _mode <= 4 else None
        speed = _data[9]
        firmware = _data1[2] / 10.0

        return {
            "battery": battery,
            "isOn": isOn,
            "oscillating": oscillating,
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
        else:
            return await self._send_command(COMMAND_STOP_OSCILLATION)

    @update_after_operation
    async def turn_on(self) -> bool:
        """Turn on the fan."""
        return await self._send_command(COMMAND_TURN_ON)

    @update_after_operation
    async def turn_off(self) -> bool:
        """Turn off the fan."""
        return await self._send_command(COMMAND_TURN_OFF)

    def get_current_percentage(self) -> Any:
        """Return cached percentage."""
        return self._get_adv_value("speed")

    def is_on(self) -> bool | None:
        """Return fan state from cache."""
        return self._get_adv_value("isOn")

    def get_oscillating_state(self) -> Any:
        """Return cached oscillating."""
        return self._get_adv_value("oscillating")

    def get_current_mode(self) -> Any:
        """Return cached mode."""
        return self._get_adv_value("mode")
