"""Base class for Keypad devices."""

from __future__ import annotations

import logging
import re

from .device import SwitchbotEncryptedDevice, SwitchbotSequenceDevice

PASSWORD_RE = re.compile(r"^\d{6,12}$")
COMMAND_GET_PASSWORD_COUNT = "570F530100"

_LOGGER = logging.getLogger(__name__)


class SwitchbotBaseKeypad(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Keypad device."""

    def _check_password_rules(self, password: str) -> None:
        """Check if the password is compliant with the rules."""
        if not PASSWORD_RE.fullmatch(password):
            raise ValueError("Password must be 6-12 digits.")

    def _build_password_payload(
        self, password: str, passcode_type: int = 0, index: int = 0xFF
    ) -> bytes:
        """Build password payload."""
        return bytes(
            [index, passcode_type, len(password), *(int(ch) for ch in password)]
        )

    def _build_add_password_cmd(
        self, password: str, passcode_type: int = 0, index: int = 0xFF
    ) -> list[str]:
        """Build command to add a password."""
        payload = self._build_password_payload(password, passcode_type, index)
        max_payload = 11
        chunks = [
            payload[i : i + max_payload] for i in range(0, len(payload), max_payload)
        ]
        total = len(chunks)
        cmds: list[str] = []

        for idx, chunk in enumerate(chunks):
            packet_info = ((total & 0x0F) << 4) | (idx & 0x0F)
            cmds.append(f"570F520202{packet_info:02X}{chunk.hex().upper()}")

        _LOGGER.debug(
            "device: %s add password commands: %s", self._device.address, cmds
        )
        return cmds

    def _parse_password_count(self, data: bytes) -> dict[str, int] | None:
        """Parse password count data."""
        if len(data) < 6 or data[0] != 0x01:
            _LOGGER.error(
                "Received truncated or malformed password count data: %s",
                data.hex(),
            )
            return None
        return {
            "pin": data[1],
            "nfc": data[2],
            "fingerprint": data[3],
            "duress_pin": data[4],
            "duress_fingerprint": data[5],
        }

    async def get_password_count(self) -> dict[str, int] | None:
        """Get the number of passwords stored in the Keypad."""
        if not (_data := await self._send_command(COMMAND_GET_PASSWORD_COUNT)):
            _LOGGER.error("Failed to get password count: empty response")
            return None
        _LOGGER.debug("Raw model %s password count data: %s", self._model, _data.hex())

        result = self._parse_password_count(_data)
        if result is not None:
            _LOGGER.debug("%s password count: %s", self._model, result)
        return result
