import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.evaporative_humidifier import (
    TARGET_HUMIDITY_MODES,
    HumidifierMode,
    HumidifierWaterLevel,
)
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
COMMAND_GET_BASIC_INFO = f"{COMMAND_HEADER}000300"

MODES_COMMANDS = {
    HumidifierMode.HIGH: "010100",
    HumidifierMode.MEDIUM: "010200",
    HumidifierMode.LOW: "010300",
    HumidifierMode.QUIET: "010400",
    HumidifierMode.TARGET_HUMIDITY: "0200",
    HumidifierMode.SLEEP: "0300",
    HumidifierMode.AUTO: "040000",
}


class SwitchbotEvaporativeHumidifier(SwitchbotEncryptedDevice):
    """Representation of a Switchbot Evaporative Humidifier"""

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

    async def _get_basic_info(self) -> bytes | None:
        """Return basic info of device."""
        _data = await self._send_command(
            key=COMMAND_GET_BASIC_INFO, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        # Not 100% sure about this data, will verify once a firmware update is available
        return {
            "firmware": _data[2] / 10.0,
        }

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(COMMAND_TURN_ON)
        if ok := self._check_command_result(result, 0, {1}):
            self._override_state({"isOn": True})
            self._fire_callbacks()
        return ok

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(COMMAND_TURN_OFF)
        if ok := self._check_command_result(result, 0, {1}):
            self._override_state({"isOn": False})
            self._fire_callbacks()
        return ok

    async def set_mode(
        self, mode: HumidifierMode, target_humidity: int | None = None
    ) -> bool:
        """Set device mode."""
        if mode == HumidifierMode.DRYING_FILTER:
            return await self.start_drying_filter()
        elif mode not in MODES_COMMANDS:
            raise ValueError("Invalid mode")

        command = COMMAND_SET_MODE + MODES_COMMANDS[mode]
        if mode in TARGET_HUMIDITY_MODES:
            if target_humidity is None:
                raise TypeError("target_humidity is required")
            command += f"{target_humidity:02x}"
        result = await self._send_command(command)
        if ok := self._check_command_result(result, 0, {1}):
            self._override_state({"mode": mode})
            if mode == HumidifierMode.TARGET_HUMIDITY and target_humidity is not None:
                self._override_state({"target_humidity": target_humidity})
            self._fire_callbacks()
        return ok

    async def set_child_lock(self, enabled: bool) -> bool:
        """Set child lock."""
        result = await self._send_command(
            COMMAND_CHILD_LOCK_ON if enabled else COMMAND_CHILD_LOCK_OFF
        )
        if ok := self._check_command_result(result, 0, {1}):
            self._override_state({"child_lock": enabled})
            self._fire_callbacks()
        return ok

    async def start_drying_filter(self):
        """Start drying filter."""
        result = await self._send_command(COMMAND_TURN_ON + "08")
        if ok := self._check_command_result(result, 0, {1}):
            self._override_state({"mode": HumidifierMode.DRYING_FILTER})
            self._fire_callbacks()
        return ok

    async def stop_drying_filter(self):
        """Stop drying filter."""
        result = await self._send_command(COMMAND_TURN_OFF)
        if ok := self._check_command_result(result, 0, {0}):
            self._override_state({"isOn": False, "mode": None})
            self._fire_callbacks()
        return ok

    def is_on(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("isOn")

    def get_mode(self) -> HumidifierMode | None:
        """Return state from cache."""
        return self._get_adv_value("mode")

    def is_child_lock_enabled(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("child_lock")

    def is_over_humidify_protection_enabled(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("over_humidify_protection")

    def is_tank_removed(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("tank_removed")

    def is_filter_missing(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("filter_missing")

    def is_filter_alert_on(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("filter_alert")

    def is_tilted_alert_on(self) -> bool | None:
        """Return state from cache."""
        return self._get_adv_value("tilted_alert")

    def get_water_level(self) -> HumidifierWaterLevel | None:
        """Return state from cache."""
        return self._get_adv_value("water_level")

    def get_filter_run_time(self) -> int | None:
        """Return state from cache."""
        return self._get_adv_value("filter_run_time")

    def get_target_humidity(self) -> int | None:
        """Return state from cache."""
        return self._get_adv_value("target_humidity")

    def get_humidity(self) -> int | None:
        """Return state from cache."""
        return self._get_adv_value("humidity")

    def get_temperature(self) -> float | None:
        """Return state from cache."""
        return self._get_adv_value("temperature")
