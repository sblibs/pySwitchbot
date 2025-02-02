import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..const import SwitchbotModel, HumidifierMode
from ..models import SwitchBotAdvertisement
from .device import SwitchbotEncryptedDevice

_LOGGER = logging.getLogger(__name__)

COMMAND_HEADER = "57"
COMMAND_GET_CK_IV = f"{COMMAND_HEADER}0f2103"
COMMAND_TURN_ON = f"{COMMAND_HEADER}0f430101"
COMMAND_TURN_OFF = f"{COMMAND_HEADER}0f430100"
COMMAND_CHILD_LOCK_ON = f"{COMMAND_HEADER}0f430501"
COMMAND_CHILD_LOCK_OFF = f"{COMMAND_HEADER}0f430500"
COMMAND_AUTO_DRY_ON = f"{COMMAND_HEADER}0f430a01"
COMMAND_AUTO_DRY_OFF = f"{COMMAND_HEADER}0f430a02"
COMMAND_SET_MODE = f"{COMMAND_HEADER}0f4302"

MODES_COMMANDS = {
    HumidifierMode.HIGH: "010100",
    HumidifierMode.MEDIUM: "010200",
    HumidifierMode.LOW: "010300",
    HumidifierMode.QUIET: "010400",
    HumidifierMode.TARGET_HUMIDITY: "0200",
    HumidifierMode.SLEEP: "030000",
    HumidifierMode.AUTO: "040000",
}


class SwitchbotEvaporativeHumidifier(SwitchbotEncryptedDevice):
    """Representation of a Switchbot relay switch 1pm."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        **kwargs: Any,
    ) -> None:
        self._force_next_update = False
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        super().update_from_advertisement(advertisement)
        _LOGGER.debug(
            "%s: update advertisement: %s",
            self.name,
            advertisement,
        )

    async def update(self, interface: int | None = None) -> None:
        """Update state of device."""
        if info := await self.get_voltage_and_current():
            self._last_full_update = time.monotonic()
            self._update_parsed_data(info)
            self._fire_callbacks()

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get the current state of the switch."""
        result = await self._send_command(COMMAND_GET_SWITCH_STATE)
        if self._check_command_result(result, 0, {1}):
            return {
                "is_on": result[1] & 0x01 != 0,
            }
        return None

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(COMMAND_TURN_ON)
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._override_state({"isOn": True})
            self._fire_callbacks()
        return ok

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(COMMAND_TURN_OFF)
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._override_state({"isOn": False})
            self._fire_callbacks()
        return ok

    async def set_mode(self, mode: HumidifierMode, target_humidity: int = None) -> None:
        if mode == HumidifierMode.DRYING_FILTER:
            return await self.start_drying_filter()
        elif mode not in MODES_COMMANDS:
            raise ValueError("Invalid mode")

        command = COMMAND_SET_MODE + MODES_COMMANDS[mode]
        if mode == HumidifierMode.TARGET_HUMIDITY:
            if target_humidity is None:
                raise TypeError("target_humidity is required")
            command += f"{target_humidity:02x}"
        result = await self._send_command(command)
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._override_state({"mode": mode})
            if mode == HumidifierMode.TARGET_HUMIDITY and target_humidity is not None:
                self._override_state({"target_humidity": target_humidity})
            self._fire_callbacks()
        return ok

    async def set_child_lock(self, enabled: bool) -> None:
        result = await self._send_command(
            COMMAND_CHILD_LOCK_ON if enabled else COMMAND_CHILD_LOCK_OFF
        )
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._fire_callbacks()
        return ok

    async def start_drying_filter(self):
        result = await self._send_command(COMMAND_TURN_ON + "08")
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._fire_callbacks()
        return ok

    async def stop_drying_filter(self):
        result = await self._send_command(COMMAND_TURN_OFF)
        ok = self._check_command_result(result, 0, {0})
        if ok:
            self._override_state({"isOn": False})
            self._fire_callbacks()
        return ok

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn")

    async def _send_command(
        self, key: str, retry: int | None = None, encrypt: bool = True
    ) -> bytes | None:
        if not encrypt:
            return await super()._send_command(key[:2] + "000000" + key[2:], retry)

        result = await self._ensure_encryption_initialized()
        if not result:
            return None

        encrypted = (
            key[:2] + self._key_id + self._iv[0:2].hex() + self._encrypt(key[2:])
        )
        result = await super()._send_command(encrypted, retry)
        return result[:1] + self._decrypt(result[4:])

    async def _ensure_encryption_initialized(self) -> bool:
        if self._iv is not None:
            return True

        result = await self._send_command(
            COMMAND_GET_CK_IV + self._key_id, encrypt=False
        )
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._iv = result[4:]

        return ok

    async def _execute_disconnect(self) -> None:
        await super()._execute_disconnect()
        self._iv = None
        self._cipher = None

    def _get_cipher(self) -> Cipher:
        if self._cipher is None:
            self._cipher = Cipher(
                algorithms.AES128(self._encryption_key), modes.CTR(self._iv)
            )
        return self._cipher

    def _encrypt(self, data: str) -> str:
        if len(data) == 0:
            return ""
        encryptor = self._get_cipher().encryptor()
        return (encryptor.update(bytearray.fromhex(data)) + encryptor.finalize()).hex()

    def _decrypt(self, data: bytearray) -> bytes:
        if len(data) == 0:
            return b""
        decryptor = self._get_cipher().decryptor()
        return decryptor.update(data) + decryptor.finalize()
