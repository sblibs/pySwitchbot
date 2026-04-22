"""Library to handle connection with Switchbot Lock."""

from __future__ import annotations

import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.lock import LockStatus
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotOperationError,
    SwitchbotSequenceDevice,
)

COMMAND_HEADER = "57"
COMMAND_LOCK_INFO = {
    SwitchbotModel.LOCK: f"{COMMAND_HEADER}0f4f8101",
    SwitchbotModel.LOCK_LITE: f"{COMMAND_HEADER}0f4f8101",
    SwitchbotModel.LOCK_PRO: f"{COMMAND_HEADER}0f4f8104",
    SwitchbotModel.LOCK_ULTRA: f"{COMMAND_HEADER}0f4f8107",
    SwitchbotModel.LOCK_VISION_PRO: f"{COMMAND_HEADER}0f4f8102",
    SwitchbotModel.LOCK_VISION: f"{COMMAND_HEADER}0f4f8102",
    SwitchbotModel.LOCK_PRO_WIFI: f"{COMMAND_HEADER}0f4f810a",
}
COMMAND_UNLOCK = {
    SwitchbotModel.LOCK: f"{COMMAND_HEADER}0f4e01011080",
    SwitchbotModel.LOCK_LITE: f"{COMMAND_HEADER}0f4e01011080",
    SwitchbotModel.LOCK_PRO: f"{COMMAND_HEADER}0f4e0101000080",
    SwitchbotModel.LOCK_ULTRA: f"{COMMAND_HEADER}0f4e0101000080",
    SwitchbotModel.LOCK_VISION_PRO: f"{COMMAND_HEADER}0f4e0101000080",
    SwitchbotModel.LOCK_VISION: f"{COMMAND_HEADER}0f4e0101000080",
    SwitchbotModel.LOCK_PRO_WIFI: f"{COMMAND_HEADER}0f4e0101000080",
}
COMMAND_UNLOCK_WITHOUT_UNLATCH = {
    SwitchbotModel.LOCK: f"{COMMAND_HEADER}0f4e010110a0",
    SwitchbotModel.LOCK_LITE: f"{COMMAND_HEADER}0f4e010110a0",
    SwitchbotModel.LOCK_PRO: f"{COMMAND_HEADER}0f4e01010000a0",
    SwitchbotModel.LOCK_ULTRA: f"{COMMAND_HEADER}0f4e01010000a0",
    SwitchbotModel.LOCK_VISION_PRO: f"{COMMAND_HEADER}0f4e01010000a0",
    SwitchbotModel.LOCK_VISION: f"{COMMAND_HEADER}0f4e01010000a0",
    SwitchbotModel.LOCK_PRO_WIFI: f"{COMMAND_HEADER}0f4e01010000a0",
}
COMMAND_LOCK = {
    SwitchbotModel.LOCK: f"{COMMAND_HEADER}0f4e01011000",
    SwitchbotModel.LOCK_LITE: f"{COMMAND_HEADER}0f4e01011000",
    SwitchbotModel.LOCK_PRO: f"{COMMAND_HEADER}0f4e0101000000",
    SwitchbotModel.LOCK_ULTRA: f"{COMMAND_HEADER}0f4e0101000000",
    SwitchbotModel.LOCK_VISION_PRO: f"{COMMAND_HEADER}0f4e0101000000",
    SwitchbotModel.LOCK_VISION: f"{COMMAND_HEADER}0f4e0101000000",
    SwitchbotModel.LOCK_PRO_WIFI: f"{COMMAND_HEADER}0f4e0101000000",
}
COMMAND_HALF_LOCK = {
    SwitchbotModel.LOCK_ULTRA: f"{COMMAND_HEADER}0f4e0101000008",
}

COMMAND_ENABLE_NOTIFICATIONS = {
    SwitchbotModel.LOCK: f"{COMMAND_HEADER}0e01001e00008101",
    SwitchbotModel.LOCK_LITE: f"{COMMAND_HEADER}0e01001e00008101",
    SwitchbotModel.LOCK_PRO: f"{COMMAND_HEADER}0e01001e00008104",
    SwitchbotModel.LOCK_ULTRA: f"{COMMAND_HEADER}0e01001e00008107",
    SwitchbotModel.LOCK_VISION_PRO: f"{COMMAND_HEADER}0e01001e00008102",
    SwitchbotModel.LOCK_VISION: f"{COMMAND_HEADER}0e01001e00008102",
    SwitchbotModel.LOCK_PRO_WIFI: f"{COMMAND_HEADER}0e01001e0000810a",
}
COMMAND_DISABLE_NOTIFICATIONS = f"{COMMAND_HEADER}0e00"

MOVING_STATUSES = {LockStatus.LOCKING, LockStatus.UNLOCKING}
BLOCKED_STATUSES = {LockStatus.LOCKING_STOP, LockStatus.UNLOCKING_STOP}
REST_STATUSES = {LockStatus.LOCKED, LockStatus.UNLOCKED, LockStatus.NOT_FULLY_LOCKED}

_LOGGER = logging.getLogger(__name__)


COMMAND_RESULT_EXPECTED_VALUES = {1, 6}
# The return value of the command is 1 when the command is successful.
# The return value of the command is 6 when the command is successful but the battery is low.


class SwitchbotLock(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Lock."""

    _model = SwitchbotModel.LOCK
    _notifications_enabled: bool = False

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel | None = None,
        **kwargs: Any,
    ) -> None:
        if model is None:
            model = self._model
        if model not in (
            SwitchbotModel.LOCK,
            SwitchbotModel.LOCK_PRO,
            SwitchbotModel.LOCK_LITE,
            SwitchbotModel.LOCK_ULTRA,
            SwitchbotModel.LOCK_VISION_PRO,
            SwitchbotModel.LOCK_VISION,
            SwitchbotModel.LOCK_PRO_WIFI,
        ):
            raise ValueError("initializing SwitchbotLock with a non-lock model")
        super().__init__(device, key_id, encryption_key, interface, model, **kwargs)

    async def lock(self) -> bool:
        """Send lock command."""
        return await self._lock_unlock(
            COMMAND_LOCK[self._model], {LockStatus.LOCKED, LockStatus.LOCKING}
        )

    async def unlock(self) -> bool:
        """Send unlock command. If unlatch feature is enabled in EU firmware, also unlatches door"""
        return await self._lock_unlock(
            COMMAND_UNLOCK[self._model], {LockStatus.UNLOCKED, LockStatus.UNLOCKING}
        )

    async def unlock_without_unlatch(self) -> bool:
        """Send unlock command. This command will not unlatch the door."""
        return await self._lock_unlock(
            COMMAND_UNLOCK_WITHOUT_UNLATCH[self._model],
            {LockStatus.UNLOCKED, LockStatus.UNLOCKING, LockStatus.NOT_FULLY_LOCKED},
        )

    async def half_lock(self) -> bool:
        """Send half lock command (Lock Ultra EU type only)."""
        if self._model not in COMMAND_HALF_LOCK:
            raise SwitchbotOperationError(
                f"Half lock is not supported on {self._model}"
            )
        if not self.is_half_lock_calibrated():
            raise SwitchbotOperationError("Half lock is not calibrated")
        return await self._lock_unlock(
            COMMAND_HALF_LOCK[self._model],
            {LockStatus.HALF_LOCKED, LockStatus.LOCKING},
        )

    def _parse_basic_data(self, basic_data: bytes) -> dict[str, Any]:
        """Parse basic data from lock."""
        return {
            "battery": basic_data[1],
            "firmware": basic_data[2] / 10.0,
        }

    async def _lock_unlock(
        self, command: str, ignore_statuses: set[LockStatus]
    ) -> bool:
        status = self.get_lock_status()
        if status is None:
            await self.update()
            status = self.get_lock_status()
        if status in ignore_statuses:
            return True

        await self._enable_notifications()
        result = await self._send_command(command)
        status = self._check_command_result(result, 0, COMMAND_RESULT_EXPECTED_VALUES)

        # Also update the battery and firmware version
        if basic_data := await self._get_basic_info():
            self._last_full_update = time.monotonic()
            if len(basic_data) >= 3:
                self._update_parsed_data(self._parse_basic_data(basic_data))
            else:
                _LOGGER.warning("Invalid basic data received: %s", basic_data)
            self._fire_callbacks()

        return status

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic status."""
        lock_raw_data = await self._get_lock_info()
        if not lock_raw_data:
            return None
        _LOGGER.debug(
            "lock_raw_data: %s, address: %s", lock_raw_data.hex(), self._device.address
        )
        basic_data = await self._get_basic_info()
        if not basic_data:
            return None
        _LOGGER.debug(
            "basic_data: %s, address: %s", basic_data.hex(), self._device.address
        )
        return self._parse_lock_data(
            lock_raw_data[1:], self._model
        ) | self._parse_basic_data(basic_data)

    def is_calibrated(self) -> Any:
        """Return True if lock is calibrated."""
        return self._get_adv_value("calibration")

    def get_lock_status(self) -> LockStatus:
        """Return lock status."""
        return self._get_adv_value("status")

    def is_door_open(self) -> bool:
        """Return True if door is open."""
        return self._get_adv_value("door_open")

    def is_unclosed_alarm_on(self) -> bool:
        """Return True if unclosed door alarm is on."""
        return self._get_adv_value("unclosed_alarm")

    def is_unlocked_alarm_on(self) -> bool:
        """Return True if lock unlocked alarm is on."""
        return self._get_adv_value("unlocked_alarm")

    def is_auto_lock_paused(self) -> bool:
        """Return True if auto lock is paused."""
        return self._get_adv_value("auto_lock_paused")

    def is_night_latch_enabled(self) -> bool:
        """Return True if Night Latch is enabled on EU firmware."""
        return self._get_adv_value("night_latch")

    def is_half_lock_calibrated(self) -> bool | None:
        """Return True if half lock position is calibrated (Lock Ultra only)."""
        return self._get_adv_value("half_lock_calibration")

    async def _get_lock_info(self) -> bytes | None:
        """Return lock info of device."""
        _data = await self._send_command(
            key=COMMAND_LOCK_INFO[self._model], retry=self._retry_count
        )

        if not self._check_command_result(_data, 0, COMMAND_RESULT_EXPECTED_VALUES):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    async def _enable_notifications(self) -> bool:
        result = await self._send_command(COMMAND_ENABLE_NOTIFICATIONS[self._model])
        return self._check_command_result(result, 0, COMMAND_RESULT_EXPECTED_VALUES)

    async def _disable_notifications(self) -> bool:
        if not self._notifications_enabled:
            return True
        result = await self._send_command(COMMAND_DISABLE_NOTIFICATIONS)
        if self._check_command_result(result, 0, COMMAND_RESULT_EXPECTED_VALUES):
            self._notifications_enabled = False
        return not self._notifications_enabled

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        if self._check_command_result(data, 0, {0xF}):
            if self._expected_disconnect:
                _LOGGER.debug(
                    "%s: Ignoring lock notification during expected disconnect",
                    self.name,
                )
                return
            self._update_lock_status(data)
        else:
            super()._notification_handler(_sender, data)

    def _update_lock_status(self, data: bytearray) -> None:
        lock_data = self._parse_lock_data(self._decrypt(data[4:]), self._model)
        if self._update_parsed_data(lock_data):
            # We leave notifications enabled in case
            # the lock is operated manually before we
            # disconnect.
            self._reset_disconnect_timer()
            self._fire_callbacks()

    @staticmethod
    def _parse_lock_data(data: bytes, model: SwitchbotModel) -> dict[str, Any]:
        if model in {SwitchbotModel.LOCK, SwitchbotModel.LOCK_VISION_PRO}:
            return {
                "calibration": bool(data[0] & 0b10000000),
                "status": LockStatus((data[0] & 0b01110000) >> 4),
                "door_open": bool(data[0] & 0b00000100),
                "unclosed_alarm": bool(data[1] & 0b00100000),
                "unlocked_alarm": bool(data[1] & 0b00010000),
            }
        if model in {SwitchbotModel.LOCK_LITE, SwitchbotModel.LOCK_VISION}:
            return {
                "calibration": bool(data[0] & 0b10000000),
                "status": LockStatus((data[0] & 0b01110000) >> 4),
                "unlocked_alarm": bool(data[1] & 0b00010000),
            }
        result = {
            "calibration": bool(data[0] & 0b10000000),
            "status": LockStatus((data[0] & 0b01111000) >> 3),
            "door_open": bool(data[1] & 0b00010000),
            "unclosed_alarm": bool(data[5] & 0b10000000),
            "unlocked_alarm": bool(data[5] & 0b01000000),
        }
        if model is SwitchbotModel.LOCK_ULTRA:
            result["half_lock_calibration"] = bool(data[1] & 0b00000001)
        return result
