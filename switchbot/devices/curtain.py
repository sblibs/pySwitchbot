"""Library to handle connection with Switchbot."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS

from ..models import SwitchBotAdvertisement
from .base_cover import COVER_COMMAND, COVER_EXT_SUM_KEY, SwitchbotBaseCover
from .device import (
    REQ_HEADER,
    CharacteristicMissingError,
    SwitchbotOperationError,
    update_after_operation,
)

# For second element of open and close arrs we should add two bytes i.e. ff00
# First byte [ff] stands for speed (00 or ff - normal, 01 - slow) *
# * Only for curtains 3. For other models use ff
# Second byte [00] is a command (00 - open, 64 - close)
OPEN_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}010100",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed + "00"
]
CLOSE_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}010164",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed + "64"
]
POSITION_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}0101",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed
]  # +actual_position
STOP_KEYS = [f"{REQ_HEADER}{COVER_COMMAND}0001", f"{REQ_HEADER}{COVER_COMMAND}00ff"]

CURTAIN_EXT_CHAIN_INFO_KEY = f"{REQ_HEADER}468101"


_LOGGER = logging.getLogger(__name__)


class SwitchbotCurtain(SwitchbotBaseCover):
    """Representation of a Switchbot Curtain."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Curtain/WoCurtain constructor."""
        # The position of the curtain is saved returned with 0 = open and 100 = closed.
        # This is independent of the calibration of the curtain bot (Open left to right/
        # Open right to left/Open from the middle).
        # The parameter 'reverse_mode' reverse these values,
        # if 'reverse_mode' = True, position = 0 equals close
        # and position = 100 equals open. The parameter is default set to True so that
        # the definition of position is the same as in Home Assistant.

        self._reverse: bool = kwargs.pop("reverse_mode", True)
        super().__init__(self._reverse, *args, **kwargs)
        self._settings: dict[str, Any] = {}
        self.ext_info_sum: dict[str, Any] = {}
        self.ext_info_adv: dict[str, Any] = {}
        self._basic_info: dict[str, Any] = {}
        self._chain_info: dict[str, Any] = {}
        self._diagnostics_interval: int | None = None
        self._last_diagnostics_attempt: float | None = None
        self._diagnostics_lock = asyncio.Lock()

    def _set_parsed_data(
        self, advertisement: SwitchBotAdvertisement, data: dict[str, Any]
    ) -> None:
        """Set data."""
        in_motion = data["inMotion"]
        previous_position = self._get_adv_value("position")
        new_position = data["position"]
        self._update_motion_direction(in_motion, previous_position, new_position)
        super()._set_parsed_data(advertisement, data)

    @update_after_operation
    async def open(self, speed: int = 255) -> bool:
        """Send open command. Speed 255 - normal, 1 - slow"""
        self._is_opening = True
        self._is_closing = False
        return await self._send_multiple_commands(
            [OPEN_KEYS[0], f"{OPEN_KEYS[1]}{speed:02X}00"]
        )

    @update_after_operation
    async def close(self, speed: int = 255) -> bool:
        """Send close command. Speed 255 - normal, 1 - slow"""
        self._is_closing = True
        self._is_opening = False
        return await self._send_multiple_commands(
            [CLOSE_KEYS[0], f"{CLOSE_KEYS[1]}{speed:02X}64"]
        )

    @update_after_operation
    async def stop(self) -> bool:
        """Send stop command to device."""
        self._is_opening = self._is_closing = False
        return await super().stop()

    @update_after_operation
    async def set_position(self, position: int, speed: int = 255) -> bool:
        """Send position command (0-100) to device. Speed 255 - normal, 1 - slow"""
        direction_adjusted_position = (100 - position) if self._reverse else position
        self._update_motion_direction(
            True, self._get_adv_value("position"), direction_adjusted_position
        )
        return await super().set_position(position, speed)

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        return self._get_adv_value("position")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        _data = await self._get_basic_info()
        if not self._valid_diagnostic_response(_data, 8):
            return None

        _position = max(min(_data[6], 100), 0)
        _direction_adjusted_position = (100 - _position) if self._reverse else _position
        _previous_position = self._get_adv_value("position")
        _in_motion = bool(_data[5] & 0b01000011)
        self._update_motion_direction(
            _in_motion, _previous_position, _direction_adjusted_position
        )

        info = {
            "battery": _data[1] if _data[1] <= 100 else None,
            "firmware": _data[2] / 10.0,
            "chainLength": _data[3],
            "openDirection": (
                "right_to_left" if _data[4] & 0b10000000 == 128 else "left_to_right"
            ),
            "touchToOpen": bool(_data[4] & 0b01000000),
            "light": bool(_data[4] & 0b00100000),
            "fault": bool(_data[4] & 0b00001000),
            "solarPanel": bool(_data[5] & 0b00001000),
            "calibration": bool(_data[5] & 0b00000100),
            "calibrated": bool(_data[5] & 0b00000100),
            "inMotion": _in_motion,
            "position": _direction_adjusted_position,
            "timers": _data[7],
        }
        self._basic_info = info
        self.diagnostic_timestamps["basic"] = time.monotonic()
        self._invalidate_secondary()
        return info

    def _update_motion_direction(
        self, in_motion: bool, previous_position: int | None, new_position: int
    ) -> None:
        """Update opening/closing status based on movement."""
        if previous_position is None:
            return
        if in_motion is False:
            self._is_closing = self._is_opening = False
            return

        if new_position != previous_position:
            self._is_opening = new_position > previous_position
            self._is_closing = new_position < previous_position

    async def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get extended info for all devices in chain."""
        _data = await self._send_command(key=COVER_EXT_SUM_KEY)

        if not self._valid_diagnostic_response(_data, 3):
            return None

        snapshot = {}
        for slot in range(2 if self._get_chain_length() == 2 else 1):
            flags = _data[1 + slot]
            snapshot[f"device{slot}"] = {
                "openDirectionDefault": not bool(flags & 0b10000000),
                "touchToOpen": bool(flags & 0b01000000),
                "light": bool(flags & 0b00100000),
                "openDirection": "left_to_right"
                if flags & 0b00010000
                else "right_to_left",
            }
        self.ext_info_sum = snapshot
        self.diagnostic_timestamps["summary"] = time.monotonic()
        return self.ext_info_sum

    def _get_chain_length(self) -> int | None:
        basic_length = self._basic_info.get("chainLength")
        chain_length = self._chain_info.get("chainLength")
        if (
            basic_length is not None
            and chain_length is not None
            and basic_length != chain_length
        ):
            return None
        return chain_length if chain_length is not None else basic_length

    def _invalidate_secondary(self) -> None:
        if self._get_chain_length() != 2:
            self.ext_info_sum.pop("device1", None)
            self.ext_info_adv.pop("device1", None)

    async def get_extended_chain_info(self) -> dict[str, Any] | None:
        """Fetch the device chain's basic status."""
        data = await self._send_command(CURTAIN_EXT_CHAIN_INFO_KEY)
        if not self._valid_diagnostic_response(data, 8) or data[3] not in (1, 2):
            return None
        motors = {}
        for slot in range(data[3]):
            offset = 4 + slot * 2
            position = data[offset] & 0x7F
            battery = data[offset + 1] & 0x7F
            motors[f"device{slot}"] = {
                "position": (100 - position) if self._reverse else position,
                "battery": battery if battery <= 100 else None,
                "solarPanel": bool(data[offset] & 0x80),
                "charging": bool(data[offset + 1] & 0x80),
            }
            if position > 100:
                motors[f"device{slot}"]["position"] = None
        self._chain_info = {"chainLength": data[3], **motors}
        self.diagnostic_timestamps["chain"] = time.monotonic()
        self._invalidate_secondary()
        return self._chain_info

    def set_diagnostics_interval(self, seconds: int | None) -> None:
        """Enable caller-driven periodic diagnostics, or disable with None."""
        if seconds is not None and (type(seconds) is not int or seconds <= 0):
            raise ValueError("Diagnostic interval must be a positive integer or None")
        self._diagnostics_interval = seconds
        self._last_diagnostics_attempt = None

    def _diagnostics_due(self) -> bool:
        return (
            self._diagnostics_interval is not None
            and self.data.get("modelFriendlyName") == "Curtain 3"
            and (
                self._last_diagnostics_attempt is None
                or time.monotonic() - self._last_diagnostics_attempt
                >= self._diagnostics_interval
            )
        )

    def poll_needed(self, seconds_since_last_poll: float | None) -> bool:
        interval = self._diagnostics_interval
        diagnostics_poll = (
            interval is not None
            and self._diagnostics_due()
            and (seconds_since_last_poll is None or seconds_since_last_poll >= interval)
        )
        return diagnostics_poll or super().poll_needed(seconds_since_last_poll)

    async def refresh_diagnostics(self) -> bool:
        """Refresh diagnostics; transport errors propagate to the caller."""
        if self.data.get("modelFriendlyName") != "Curtain 3":
            return False
        async with self._diagnostics_lock:
            self._last_diagnostics_attempt = time.monotonic()
            try:
                info = await self.get_basic_info()
                if info is not None:
                    self._update_parsed_data(info)
                chain = await self.get_extended_chain_info()
                summary = await self.get_extended_info_summary()
                advanced = await self.get_extended_info_adv()
                return (
                    all(page is not None for page in (info, chain, summary, advanced))
                    and self._get_chain_length() is not None
                )
            finally:
                self._fire_callbacks()

    async def update(self, interface: int | None = None) -> None:
        await super().update(interface)
        if not self._diagnostics_due() or self._get_adv_value("inMotion") is not False:
            return
        try:
            await self.refresh_diagnostics()
        except (
            *BLEAK_RETRY_EXCEPTIONS,
            CharacteristicMissingError,
            SwitchbotOperationError,
        ):
            _LOGGER.debug(
                "%s: Optional diagnostic refresh failed", self.name, exc_info=True
            )
