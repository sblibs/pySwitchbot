"""Keypad Vision (Pro) device handling."""

from __future__ import annotations

import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from .base_keypad import (
    COMMAND_GET_PASSWORD_COUNT,
    PASSWORD_RE,
    SwitchbotBaseKeypad,
)

_LOGGER = logging.getLogger(__name__)

__all__ = ["COMMAND_GET_PASSWORD_COUNT", "PASSWORD_RE", "SwitchbotKeypadVision"]


class SwitchbotKeypadVision(SwitchbotBaseKeypad):
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
        super().__init__(device, key_id, encryption_key, model=model, **kwargs)

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
        if len(_data) < 15:
            _LOGGER.error(
                "Received truncated or malformed basic info data: %s",
                _data.hex(),
            )
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

    def _parse_password_count(self, data: bytes) -> dict[str, int] | None:
        """Parse password count data."""
        result = super()._parse_password_count(data)
        if result is None:
            return None
        if self._model == SwitchbotModel.KEYPAD_VISION_PRO:
            if len(data) < 8:
                _LOGGER.error(
                    "Received truncated password count data for %s: %s",
                    self._model,
                    data.hex(),
                )
                return None
            result.update(
                {
                    "face": data[6],
                    "palm_vein": data[7],
                }
            )
        return result

    async def add_password(self, password: str) -> bool:
        """Add a password to the Keypad Vision (Pro)."""
        self._check_password_rules(password)
        cmds = self._build_add_password_cmd(password)
        return await self._send_command_sequence(cmds)
