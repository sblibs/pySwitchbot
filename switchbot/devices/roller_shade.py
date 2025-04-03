"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
from typing import Any

from ..models import SwitchBotAdvertisement
from .base_cover import CONTROL_SOURCE, ROLLERSHADE_COMMAND, SwitchbotBaseCover
from .device import REQ_HEADER, SwitchbotSequenceDevice, update_after_operation

_LOGGER = logging.getLogger(__name__)


OPEN_KEYS = [
    f"{REQ_HEADER}{ROLLERSHADE_COMMAND}01{CONTROL_SOURCE}0100",
    f"{REQ_HEADER}{ROLLERSHADE_COMMAND}05{CONTROL_SOURCE}0000",
]
CLOSE_KEYS = [
    f"{REQ_HEADER}{ROLLERSHADE_COMMAND}01{CONTROL_SOURCE}0164",
    f"{REQ_HEADER}{ROLLERSHADE_COMMAND}05{CONTROL_SOURCE}0064",
]
POSITION_KEYS = [
    f"{REQ_HEADER}{ROLLERSHADE_COMMAND}01{CONTROL_SOURCE}01",
    f"{REQ_HEADER}{ROLLERSHADE_COMMAND}05{CONTROL_SOURCE}",
]  # +actual_position
STOP_KEYS = [f"{REQ_HEADER}{ROLLERSHADE_COMMAND}00{CONTROL_SOURCE}01"]


class SwitchbotRollerShade(SwitchbotBaseCover, SwitchbotSequenceDevice):
    """Representation of a Switchbot Roller Shade."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot roller shade constructor."""
        # The position of the roller shade is saved returned with 0 = open and 100 = closed.
        # the definition of position is the same as in Home Assistant.

        self._reverse: bool = kwargs.pop("reverse_mode", True)
        super().__init__(self._reverse, *args, **kwargs)

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
    async def open(self, mode: int = 0) -> bool:
        """Send open command. 0 - performance mode, 1 - unfelt mode."""
        self._is_opening = True
        self._is_closing = False
        return await self._send_multiple_commands(OPEN_KEYS)

    @update_after_operation
    async def close(self, speed: int = 0) -> bool:
        """Send close command. 0 - performance mode, 1 - unfelt mode."""
        self._is_closing = True
        self._is_opening = False
        return await self._send_multiple_commands(CLOSE_KEYS)

    @update_after_operation
    async def stop(self) -> bool:
        """Send stop command to device."""
        self._is_opening = self._is_closing = False
        return await self._send_multiple_commands(STOP_KEYS)

    @update_after_operation
    async def set_position(self, position: int, mode: int = 0) -> bool:
        """Send position command (0-100) to device. 0 - performance mode, 1 - unfelt mode."""
        position = (100 - position) if self._reverse else position
        self._update_motion_direction(True, self._get_adv_value("position"), position)
        return await self._send_multiple_commands(
            [
                f"{POSITION_KEYS[0]}{position:02X}",
                f"{POSITION_KEYS[1]}{mode:02X}{position:02X}",
            ]
        )

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        return self._get_adv_value("position")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        _position = max(min(_data[5], 100), 0)
        _direction_adjusted_position = (100 - _position) if self._reverse else _position
        _previous_position = self._get_adv_value("position")
        _in_motion = bool(_data[4] & 0b00000011)
        self._update_motion_direction(
            _in_motion, _previous_position, _direction_adjusted_position
        )

        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "chainLength": _data[3],
            "openDirection": (
                "clockwise" if _data[4] & 0b10000000 == 128 else "anticlockwise"
            ),
            "fault": bool(_data[4] & 0b00010000),
            "solarPanel": bool(_data[4] & 0b00001000),
            "calibration": bool(_data[4] & 0b00000100),
            "calibrated": bool(_data[4] & 0b00000100),
            "inMotion": _in_motion,
            "position": _direction_adjusted_position,
            "timers": _data[6],
        }

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
