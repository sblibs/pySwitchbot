"""Keypad Vision (Pro) device handling."""

import logging
import re
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from .device import SwitchbotEncryptedDevice, SwitchbotSequenceDevice

PASSWORD_RE = re.compile(r"^\d{6,12}$")
COMMAND_GET_PASSWORD_COUNT = "570F530100"

_LOGGER = logging.getLogger(__name__)


class SwitchbotKeypadVision(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Keypad Vision (Pro) device."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel,
        **kwargs: Any,
    ) -> None:
        """Initialize Keypad Vision (Pro) device."""
        super().__init__(device, key_id, encryption_key, model, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        _LOGGER.debug("Raw model %s basic info data: %s", self._model, _data.hex())

        battery = _data[1] & 0x7F
        firmware = _data[2] / 10.0
        hardware = _data[3]
        support_fingerprint = _data[4]
        lock_button_enabled = bool(_data[5] != 1)
        tamper_alarm_enabled = bool(_data[9])
        backlight_enabled = bool(_data[10] != 1)
        backlight_level = _data[11]
        prompt_tone_enabled = bool(_data[12] != 1)

        if self._model == SwitchbotModel.KEYPAD_VISION:
            battery_charging = bool((_data[14] & 0x06) >> 1)
        else:
            battery_charging = bool((_data[14] & 0x0E) >> 1)

        result = {
            "battery": battery,
            "firmware": firmware,
            "hardware": hardware,
            "support_fingerprint": support_fingerprint,
            "lock_button_enabled": lock_button_enabled,
            "tamper_alarm_enabled": tamper_alarm_enabled,
            "backlight_enabled": backlight_enabled,
            "backlight_level": backlight_level,
            "prompt_tone_enabled": prompt_tone_enabled,
            "battery_charging": battery_charging,
        }

        _LOGGER.debug("%s basic info: %s", self._model, result)
        return result

    def _check_password_rules(self, password: str) -> None:
        """Check if the password compliant with the rules."""
        if not PASSWORD_RE.fullmatch(password):
            raise ValueError("Password must be 6-12 digits.")

    def _build_password_payload(self, password: str) -> bytes:
        """Build password payload."""
        pwd_bytes = bytes(int(ch) for ch in password)
        pwd_length = len(pwd_bytes)

        payload = bytearray()
        payload.append(0xFF)
        payload.append(0x00)
        payload.append(pwd_length)
        payload.extend(pwd_bytes)

        return bytes(payload)

    def _build_add_password_cmd(self, password: str) -> list[str]:
        """Build command to add a password."""
        cmd_header = bytes.fromhex("570F520202")

        payload = self._build_password_payload(password)

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

    async def add_password(self, password: str) -> bool:
        """Add a password to the Keypad Vision (Pro)."""
        self._check_password_rules(password)
        cmds = self._build_add_password_cmd(password)
        return await self._send_command_sequence(cmds)

    async def get_password_count(self) -> dict[str, int] | None:
        """Get the number of passwords stored in the Keypad Vision (Pro)."""
        if not (_data := await self._send_command(COMMAND_GET_PASSWORD_COUNT)):
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

        if self._model == SwitchbotModel.KEYPAD_VISION_PRO:
            face = _data[6]
            palm_vein = _data[7]
            result.update(
                {
                    "face": face,
                    "palm_vein": palm_vein,
                }
            )

        _LOGGER.debug("%s password count: %s", self._model, result)
        return result
