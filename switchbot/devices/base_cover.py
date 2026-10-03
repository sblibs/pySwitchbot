"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
import time
from abc import abstractmethod
from typing import Any

from ..const.curtain import CURTAIN_CHARGING_STATES, CurtainChargingState
from .device import REQ_HEADER, SwitchbotDevice, update_after_operation

# Cover keys
COVER_COMMAND = "4501"
ROLLERSHADE_COMMAND = "4701"
CONTROL_SOURCE = "00"

# For second element of open and close arrs we should add two bytes i.e. ff00
# First byte [ff] stands for speed (00 or ff - normal, 01 - slow) *
# * Only for curtains 3. For other models use ff
# Second byte [00] is a command (00 - open, 64 - close)
POSITION_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}0101",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed
]  # +actual_position
STOP_KEYS = [f"{REQ_HEADER}{COVER_COMMAND}0001", f"{REQ_HEADER}{COVER_COMMAND}00ff"]

COVER_EXT_SUM_KEY = f"{REQ_HEADER}460401"
COVER_EXT_ADV_KEY = f"{REQ_HEADER}460402"


_LOGGER = logging.getLogger(__name__)


class SwitchbotBaseCover(SwitchbotDevice):
    """Representation of a Switchbot Cover devices for both curtains and tilt blinds."""

    def __init__(self, reverse: bool, *args: Any, **kwargs: Any) -> None:
        """Switchbot Cover device constructor."""
        super().__init__(*args, **kwargs)
        self._reverse = reverse
        self._settings: dict[str, Any] = {}
        self.ext_info_sum: dict[str, Any] = {}
        self.ext_info_adv: dict[str, Any] = {}
        self.diagnostic_timestamps: dict[str, float] = {}
        self._is_opening: bool = False
        self._is_closing: bool = False

    @update_after_operation
    async def stop(self) -> bool:
        """Send stop command to device."""
        return await self._send_multiple_commands(STOP_KEYS)

    @update_after_operation
    async def set_position(self, position: int, speed: int = 255) -> bool:
        """Send position command (0-100) to device. Speed 255 - normal, 1 - slow"""
        position = (100 - position) if self._reverse else position
        return await self._send_multiple_commands(
            [
                f"{POSITION_KEYS[0]}{position:02X}",
                f"{POSITION_KEYS[1]}{speed:02X}{position:02X}",
            ]
        )

    @abstractmethod
    def get_position(self) -> Any:
        """Return current device position."""

    @abstractmethod
    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""

    @abstractmethod
    async def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get extended info for all devices in chain."""

    async def get_extended_info_adv(self) -> dict[str, Any] | None:
        """Get advance page info for device chain."""
        _data = await self._send_command(key=COVER_EXT_ADV_KEY)
        if not self._valid_diagnostic_response(_data, 7):
            return None

        snapshot = {}
        for slot in range(2 if self._get_chain_length() == 2 else 1):
            offset = 1 + slot * 3
            raw_state = _data[offset + 2]
            charging_state = CURTAIN_CHARGING_STATES.get(raw_state)
            legacy_state = {
                CurtainChargingState.ADAPTER_FULL: "fully_charged",
                CurtainChargingState.SOLAR_FULL: "fully_charged",
                CurtainChargingState.HARDWARE_ERROR: "charging_error",
            }.get(charging_state, charging_state)
            snapshot[f"device{slot}"] = {
                "battery": _data[offset] if _data[offset] <= 100 else None,
                "firmware": _data[offset + 1] / 10.0,
                "stateOfCharge": str(legacy_state)
                if legacy_state is not None
                else None,
                "chargingState": charging_state,
                "chargingStateRaw": raw_state,
            }
        self.ext_info_adv = snapshot
        self.diagnostic_timestamps["advanced"] = time.monotonic()
        return self.ext_info_adv

    def _get_chain_length(self) -> int | None:
        return self.parsed_data.get("chainLength", self.parsed_data.get("deviceChain"))

    @staticmethod
    def _valid_diagnostic_response(data: bytes | None, minimum_length: int) -> bool:
        return (
            isinstance(data, (bytes, bytearray))
            and len(data) >= minimum_length
            and data[0] == 1
        )

    def get_light_level(self) -> Any:
        """Return cached light level."""
        # To get actual light level call update() first.
        return self._get_adv_value("lightLevel")

    def is_reversed(self) -> bool:
        """Return True if curtain position is opposite from SB data."""
        return self._reverse

    def is_calibrated(self) -> Any:
        """Return True curtain is calibrated."""
        # To get actual light level call update() first.
        return self._get_adv_value("calibration")

    def is_opening(self) -> bool:
        """Return True if the curtain is opening."""
        return self._is_opening

    def is_closing(self) -> bool:
        """Return True if the curtain is closing."""
        return self._is_closing
