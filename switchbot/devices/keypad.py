"""Keypad device handling."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

import aiohttp

from ..const import SwitchbotModel
from .base_keypad import (
    COMMAND_GET_PASSWORD_COUNT,
    PASSWORD_RE,
    SwitchbotBaseKeypad,
)
from .device import SwitchbotOperationError

_LOGGER = logging.getLogger(__name__)

__all__ = ["COMMAND_GET_PASSWORD_COUNT", "PASSWORD_RE", "SwitchbotKeypad"]


class SwitchbotKeypad(SwitchbotBaseKeypad):
    """Representation of a Switchbot Keypad device."""

    _model = SwitchbotModel.KEYPAD

    @property
    def attempt_state(self) -> int | None:
        """Return the last attempt state from advertisement data."""
        return self._get_adv_value("attempt_state")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        if len(_data) < 3:
            _LOGGER.error(
                "Received truncated or malformed basic info data: %s",
                _data.hex(),
            )
            return None
        _LOGGER.debug("Raw model %s basic info data: %s", self._model, _data.hex())

        battery = _data[1] & 0x7F
        firmware = _data[2] / 10.0
        hardware = _data[3] if len(_data) > 3 else None

        result = {
            "battery": battery,
            "firmware": firmware,
            "hardware": hardware,
        }

        _LOGGER.debug("%s basic info: %s", self._model, result)
        return result

    def _validate_passcode_params(
        self,
        passcode_type: int,
        start_time: int | None,
        end_time: int | None,
    ) -> None:
        """Validate passcode type and active window duration."""
        if passcode_type not in (0, 1, 2, 3):
            raise ValueError(f"Invalid passcode_type: {passcode_type}")

        if start_time is not None and not (0 <= start_time <= 0xFFFFFFFF):
            raise ValueError(f"Invalid start_time: {start_time}")

        if end_time is not None and not (0 <= end_time <= 0xFFFFFFFF):
            raise ValueError(f"Invalid end_time: {end_time}")

        if passcode_type == 1 and (not start_time or not end_time):
            raise ValueError(
                "start_time and end_time are required when passcode_type is 1 (timeLimit)"
            )

        if (
            start_time is not None
            and end_time is not None
            and end_time != 0
            and end_time < start_time
        ):
            raise ValueError(
                f"end_time ({end_time}) must be greater than or equal to start_time ({start_time})"
            )

    def _validate_cloud_credentials(
        self,
        session: aiohttp.ClientSession | None,
        token: str | None,
        region: str | None,
    ) -> None:
        """Validate cloud synchronization credentials."""
        cloud_params = (session, token, region)
        if any(p is not None for p in cloud_params) and not all(
            p is not None for p in cloud_params
        ):
            raise ValueError(
                "To synchronize with SwitchBot Cloud, 'session', 'token', and 'region' must all be provided."
            )
        if region is not None and not re.fullmatch(r"[a-z]{2,8}", region):
            raise ValueError(f"Invalid region: {region}")
        if token is not None and not token.strip():
            raise ValueError("Token must not be empty.")

    async def _add_passcode_to_device(self, password: str, passcode_type: int) -> int:
        """Add passcode to physical device over BLE and return the assigned index."""
        cmds = self._build_add_password_cmd(password, passcode_type, index=0xFF)

        result = None
        for cmd in cmds:
            result = await self._send_command(cmd)
            if not result or result[0] != 0x01:
                result_hex = result.hex() if result else "None"
                raise SwitchbotOperationError(
                    f"Failed to add password (result={result_hex})"
                )

        if not result or len(result) < 3:
            raise SwitchbotOperationError(
                "Failed to retrieve passcode index from keypad response."
            )

        return result[2]

    async def _rollback_passcode(
        self, assigned_index: int, prefix: str, err: Exception | None = None
    ) -> None:
        """Roll back a provisioned passcode on failure."""
        _LOGGER.error(
            "%s. Rolling back and deleting passcode from keypad memory.",
            prefix,
        )
        success = False
        rollback_err: Exception | None = None
        try:
            success = await self.delete_password(assigned_index)
        except Exception as ex:
            rollback_err = ex
            _LOGGER.exception("Failed to delete passcode from keypad during rollback.")
        if not success:
            msg = (
                f"{prefix}. Rollback failed: "
                f"passcode at index {assigned_index} may still be active on the device."
            )
            cause = rollback_err or err
            if cause is not None:
                raise SwitchbotOperationError(msg) from cause
            raise SwitchbotOperationError(msg)

    async def _set_passcode_time_window(
        self,
        assigned_index: int,
        start_time: int | None,
        end_time: int | None,
    ) -> None:
        """Set active time window for passcode, rolling back on failure."""
        start = start_time if start_time is not None else 0
        end = end_time if end_time is not None else 0
        time_cmd = f"570F520203{assigned_index:02X}{start:08X}{end:08X}"
        prefix = "Failed to set active time window for passcode"

        try:
            time_result = await self._send_command(time_cmd)
        except Exception as err:
            await self._rollback_passcode(assigned_index, prefix, err)
            raise

        if not time_result or time_result[0] != 0x01:
            await self._rollback_passcode(assigned_index, prefix)
            result_hex = time_result.hex() if time_result else "None"
            raise SwitchbotOperationError(
                f"Failed to set active time window for passcode (result={result_hex})"
            )

    async def _sync_passcode_to_cloud(  # noqa: PLR0913, PLR0917
        self,
        assigned_index: int,
        password: str,
        passcode_type: int,
        start_time: int | None,
        end_time: int | None,
        session: aiohttp.ClientSession,
        token: str,
        region: str,
        name: str | None,
        creator: str | None,
    ) -> None:
        """Synchronize provisioned passcode to SwitchBot Cloud."""
        start = start_time if start_time is not None else 0
        end = end_time if end_time is not None else 0
        clean_mac = self._device.address.replace(":", "").replace("-", "").upper()
        key_types = {0: "permanent", 1: "timeLimit", 2: "disposable", 3: "urgent"}
        key_type_str = key_types[passcode_type]

        payload = {
            "deviceID": clean_mac,
            "functionID": 4245,
            "params": {
                "0": assigned_index,
                "1": 1,  # Credential Type: 1 = passcode
                "2": start,
                "3": end,
                "4": key_type_str,
                "5": name or f"pySwitchbot_{assigned_index}",
                "6": password,
                "7": creator or "pySwitchbot",
            },
            "notify": {"url": "ignored_url", "type": "mqtt"},
            "optSrc": "app",
            "timeout": 30000,
            "requestId": str(uuid.uuid4()),
        }

        headers = {
            "authorization": token,
        }

        try:
            await self.api_request(
                session,
                f"wonderlabs.{region}",
                "command/cmd/api/v1/func/invoke",
                payload,
                headers,
            )
        except Exception as err:
            prefix = (
                f"SwitchBot Cloud sync failed for passcode at index {assigned_index}"
            )
            await self._rollback_passcode(assigned_index, prefix, err)
            raise

    async def add_password(  # noqa: PLR0913
        self,
        password: str,
        passcode_type: int = 0,
        start_time: int | None = None,
        end_time: int | None = None,
        *,
        session: aiohttp.ClientSession | None = None,
        token: str | None = None,
        region: str | None = None,
        name: str | None = None,
        creator: str | None = None,
    ) -> int:
        """Add a passcode to the Keypad and optionally synchronize it to the cloud."""
        self._check_password_rules(password)
        self._validate_passcode_params(passcode_type, start_time, end_time)
        self._validate_cloud_credentials(session, token, region)

        assigned_index = await self._add_passcode_to_device(password, passcode_type)
        await self._set_passcode_time_window(assigned_index, start_time, end_time)

        if session is not None and token is not None and region is not None:
            await self._sync_passcode_to_cloud(
                assigned_index=assigned_index,
                password=password,
                passcode_type=passcode_type,
                start_time=start_time,
                end_time=end_time,
                session=session,
                token=token,
                region=region,
                name=name,
                creator=creator,
            )

        return assigned_index

    async def modify_password(
        self,
        index: int,
        password: str,
        passcode_type: int = 0,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> None:
        """Modify an existing passcode on the Keypad."""
        if not (0 <= index <= 0xFF):
            raise ValueError(f"Invalid index: {index}")
        self._check_password_rules(password)
        self._validate_passcode_params(passcode_type, start_time, end_time)

        cmds = self._build_add_password_cmd(password, passcode_type, index=index)

        for cmd in cmds:
            result = await self._send_command(cmd)
            if not result or result[0] != 0x01:
                result_hex = result.hex() if result else "None"
                raise SwitchbotOperationError(
                    f"Failed to modify password (result={result_hex})"
                )

        start = start_time if start_time is not None else 0
        end = end_time if end_time is not None else 0

        time_cmd = f"570F520203{index:02X}{start:08X}{end:08X}"
        time_result = await self._send_command(time_cmd)
        if not time_result or time_result[0] != 0x01:
            result_hex = time_result.hex() if time_result else "None"
            raise SwitchbotOperationError(
                f"Failed to set active time window for passcode at index {index}; passcode was updated on device (result={result_hex})"
            )

    async def delete_password(self, index: int) -> bool:
        """Delete a passcode from the Keypad."""
        if not (0 <= index <= 0xFF):
            raise ValueError(f"Invalid index: {index}")
        delete_cmd = f"570F520205{index:02X}"
        result = await self._send_command(delete_cmd)
        if not result or result[0] != 0x01:
            _LOGGER.error(
                "Failed to delete passcode at index %d (result=%s)",
                index,
                result.hex() if result else "None",
            )
            return False
        return True

    async def sync_time(self, timestamp: int | None = None) -> bool:
        """Synchronize the Keypad's internal clock (RTC) with system time."""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        elif timestamp < 10000000000:
            timestamp *= 1000

        if not (0 <= timestamp <= 0xFFFFFFFFFFFFFFFF):
            raise ValueError(f"Invalid timestamp in milliseconds: {timestamp}")

        time_hex = f"{timestamp:016X}"
        cmd = f"57000501{time_hex}"
        result = await self._send_command(cmd)
        if not result or result[0] != 0x01:
            _LOGGER.error(
                "Failed to sync keypad time (result=%s)",
                result.hex() if result else "None",
            )
            return False
        return True
