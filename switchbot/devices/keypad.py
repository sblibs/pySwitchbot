"""Keypad device handling."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

import aiohttp
from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotOperationError,
    SwitchbotSequenceDevice,
)

PASSWORD_RE = re.compile(r"^\d{6,12}$")
COMMAND_GET_PASSWORD_COUNT = "570F530100"

_LOGGER = logging.getLogger(__name__)


class SwitchbotKeypad(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Keypad device."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.KEYPAD,
        **kwargs: Any,
    ) -> None:
        """Initialize Keypad device."""
        super().__init__(device, key_id, encryption_key, model=model, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.KEYPAD,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

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

    def _check_password_rules(self, password: str) -> None:
        """Check if the password is compliant with the rules."""
        if not PASSWORD_RE.fullmatch(password):
            raise ValueError("Password must be 6-12 digits.")

    def _validate_passcode_params(  # noqa: PLR0913
        self,
        passcode_type: int,
        start_time: int | None,
        end_time: int | None,
        region: str | None = None,
        session: aiohttp.ClientSession | None = None,
        token: str | None = None,
    ) -> None:
        """Validate passcode type, active window duration, region, and partial credentials."""
        if passcode_type not in (0, 1, 2, 3):
            raise ValueError(f"Invalid passcode_type: {passcode_type}")

        if start_time is not None and not (0 <= start_time <= 0xFFFFFFFF):
            raise ValueError(f"Invalid start_time: {start_time}")

        if end_time is not None and not (0 <= end_time <= 0xFFFFFFFF):
            raise ValueError(f"Invalid end_time: {end_time}")

        if region is not None and not re.fullmatch(r"[a-z]{2,8}", region):
            raise ValueError(f"Invalid region: {region}")

        # Check for partial credentials
        cloud_params = [session, token, region]
        any_provided = any(p is not None for p in cloud_params)
        all_provided = all(p is not None for p in cloud_params)
        if any_provided and not all_provided:
            raise ValueError(
                "To synchronize with SwitchBot Cloud, 'session', 'token', and 'region' must all be provided."
            )

    def _build_password_payload(
        self, password: str, passcode_type: int, index: int
    ) -> bytes:
        """Build password payload."""
        pwd_bytes = bytes(int(ch) for ch in password)
        pwd_length = len(pwd_bytes)

        payload = bytearray()
        payload.append(index)
        payload.append(passcode_type)
        payload.append(pwd_length)
        payload.extend(pwd_bytes)

        return bytes(payload)

    def _build_add_password_cmd(
        self, password: str, passcode_type: int, index: int
    ) -> list[str]:
        """Build command to add a password."""
        cmd_header = bytes.fromhex("570F520202")

        payload = self._build_password_payload(password, passcode_type, index)

        max_payload = 11

        chunks = [
            payload[i : i + max_payload] for i in range(0, len(payload), max_payload)
        ]
        total = len(chunks)
        cmds: list[str] = []

        for idx, chunk in enumerate(chunks):
            packet_info = ((total & 0x0F) << 4) | (idx & 0x0F)

            cmd = bytearray()
            cmd.extend(cmd_header)
            cmd.append(packet_info)
            cmd.extend(chunk)

            cmds.append(cmd.hex().upper())

        _LOGGER.debug(
            "device: %s add password commands: %s", self._device.address, cmds
        )

        return cmds

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
        """
        Add a passcode to the Keypad and optionally synchronize it to the cloud.

        This method sends the passcode value and active validity window to the physical
        keypad over BLE. If cloud sync credentials (session, token, and region) are provided,
        it also reports the new passcode to the SwitchBot Cloud database so it appears
        correctly in the official smartphone app.

        Args:
            password: A string of 6-12 numeric digits representing the passcode.
            passcode_type: Passcode type classification (0 = Permanent, 1 = Time-limited/Temporary,
                2 = One-time/Disposable, 3 = Emergency/Urgent).
            start_time: Unix timestamp in seconds for when the passcode becomes active.
                Only applicable if passcode_type is 1 (Time-limited). Defaults to 0 (always active).
            end_time: Unix timestamp in seconds for when the passcode expires.
                Only applicable if passcode_type is 1 (Time-limited). Defaults to 0 (never expires).
            session: Optional client session to perform the cloud HTTP request.
            token: Optional SwitchBot authorization token/JWT for the cloud request.
            region: Optional regional subdomain for API routing (e.g. "us", "jp").
            name: Optional display name for the credential (e.g. "Guest Code").
                If not specified, defaults to "pySwitchbot_[index]".
            creator: Optional creator identifier (e.g. "pySwitchbot").

        Returns:
            The passcode index (0-255) assigned to this passcode by the Keypad.

        Raises:
            ValueError: If the passcode does not meet the 6-12 digit constraint.
            SwitchbotOperationError: If the BLE write command to the keypad fails or
                if the active validity window cannot be configured.
            SwitchbotApiError: If the cloud API sync request fails.

        """
        self._check_password_rules(password)
        self._validate_passcode_params(
            passcode_type, start_time, end_time, region, session, token
        )

        assigned_index = await self._add_passcode_to_device(password, passcode_type)

        # Set active time window if start/end time are supplied or type is time-limited
        start = start_time if start_time is not None else 0
        end = end_time if end_time is not None else 0

        time_cmd = f"570F520203{assigned_index:02X}{start.to_bytes(4, 'big').hex().upper()}{end.to_bytes(4, 'big').hex().upper()}"
        time_result = await self._send_command(time_cmd)
        if not time_result or time_result[0] != 0x01:
            success = False
            try:
                success = await self.delete_password(assigned_index)
            except Exception:
                _LOGGER.exception(
                    "Failed to delete passcode from keypad during rollback after time window write failed."
                )
            if not success:
                raise SwitchbotOperationError(
                    f"Failed to set active time window for passcode. Rollback failed: passcode at index {assigned_index} may still be active on the device."
                )
            raise SwitchbotOperationError(
                "Failed to set active time window for passcode."
            )

        # Sync to SwitchBot Cloud if credentials are provided
        if session and token and region:
            clean_mac = self._device.address.replace(":", "").replace("-", "").upper()
            key_types = {0: "permanent", 1: "timeLimit", 2: "disposable", 3: "urgent"}
            key_type_str = key_types.get(passcode_type, "permanent")

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
                _LOGGER.exception(
                    "SwitchBot Cloud sync failed for passcode at index %d. "
                    "Rolling back and deleting passcode from keypad memory.",
                    assigned_index,
                )
                success = False
                try:
                    success = await self.delete_password(assigned_index)
                except Exception:
                    _LOGGER.exception(
                        "Failed to delete passcode from keypad during rollback."
                    )
                if not success:
                    raise SwitchbotOperationError(
                        f"SwitchBot Cloud sync failed for passcode at index {assigned_index}. Rollback failed: passcode at index {assigned_index} may still be active on the device."
                    ) from err
                raise

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
        self._check_password_rules(password)
        self._validate_passcode_params(passcode_type, start_time, end_time)

        cmds = self._build_add_password_cmd(password, passcode_type, index=index)

        try:
            for cmd in cmds:
                result = await self._send_command(cmd)
                if not result or result[0] != 0x01:
                    result_hex = result.hex() if result else "None"
                    raise SwitchbotOperationError(
                        f"Failed to modify password (result={result_hex})"
                    )
        except Exception as err:
            _LOGGER.exception(
                "Failed to send modify password commands for index %d. "
                "Rolling back and deleting passcode from keypad memory.",
                index,
            )
            success = False
            try:
                success = await self.delete_password(index)
            except Exception:
                _LOGGER.exception(
                    "Failed to delete passcode from keypad during rollback after modify passcode write failed."
                )
            if not success:
                raise SwitchbotOperationError(
                    f"Failed to modify password for index {index}. Rollback failed: passcode at index {index} may still be active on the device or in an indeterminate state."
                ) from err
            raise

        start = start_time if start_time is not None else 0
        end = end_time if end_time is not None else 0

        time_cmd = f"570F520203{index:02X}{start.to_bytes(4, 'big').hex().upper()}{end.to_bytes(4, 'big').hex().upper()}"
        time_result = await self._send_command(time_cmd)
        if not time_result or time_result[0] != 0x01:
            success = False
            try:
                success = await self.delete_password(index)
            except Exception:
                _LOGGER.exception(
                    "Failed to delete passcode from keypad during rollback after time window write failed."
                )
            if not success:
                raise SwitchbotOperationError(
                    f"Failed to set active time window for passcode. Rollback failed: passcode at index {index} may still be active on the device."
                )
            raise SwitchbotOperationError(
                "Failed to set active time window for passcode."
            )

    async def delete_password(self, index: int) -> bool:
        """Delete a passcode from the Keypad."""
        delete_cmd = f"570F520205{index:02X}"
        result = await self._send_command(delete_cmd)
        return bool(result and result[0] == 0x01)

    async def get_password_count(self) -> dict[str, int] | None:
        """Get the number of passwords stored in the Keypad."""
        if not (_data := await self._send_command(COMMAND_GET_PASSWORD_COUNT)):
            return None
        if len(_data) < 6:
            _LOGGER.error(
                "Received truncated or malformed password count data: %s",
                _data.hex(),
            )
            return None
        _LOGGER.debug("Raw model %s password count data: %s", self._model, _data.hex())

        pin = _data[1]
        nfc = _data[2]
        fingerprint = _data[3]
        duress_pin = _data[4]
        duress_fingerprint = _data[5]

        result = {
            "pin": pin,
            "nfc": nfc,
            "fingerprint": fingerprint,
            "duress_pin": duress_pin,
            "duress_fingerprint": duress_fingerprint,
        }

        _LOGGER.debug("%s password count: %s", self._model, result)
        return result

    async def sync_time(self, timestamp: int | None = None) -> bool:
        """
        Synchronize the Keypad's internal clock (RTC) with system time.

        This method sends an 8-byte big-endian timestamp to the keypad. The keypad
        expects this timestamp in milliseconds. If a standard 4-byte second-level
        timestamp (e.g. Unix epoch in seconds) is provided, it is scaled to milliseconds.

        Args:
            timestamp: The timestamp to set the clock to (in milliseconds or seconds).
                If None, the current computer system time in milliseconds is used.

        Returns:
            True if the keypad clock was successfully synchronized, False otherwise.

        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        elif timestamp < 10000000000:
            timestamp *= 1000

        time_hex = f"{timestamp:016X}"
        cmd = f"57000501{time_hex}"
        result = await self._send_command(cmd)
        return bool(result and result[0] == 0x01)
