import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..adv_parsers.humidifier import calculate_temperature_and_humidity
from ..const import SwitchbotModel
from ..const.evaporative_humidifier import (
    TARGET_HUMIDITY_MODES,
    HumidifierAction,
    HumidifierMode,
    HumidifierWaterLevel,
)
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotOperationError,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)

COMMAND_HEADER = "57"
COMMAND_GET_CK_IV = f"{COMMAND_HEADER}0f2103"
COMMAND_TURN_ON = f"{COMMAND_HEADER}0f430101"
COMMAND_CHILD_LOCK_ON = f"{COMMAND_HEADER}0f430501"
COMMAND_CHILD_LOCK_OFF = f"{COMMAND_HEADER}0f430500"
COMMAND_AUTO_DRY_ON = f"{COMMAND_HEADER}0f430a01"
COMMAND_AUTO_DRY_OFF = f"{COMMAND_HEADER}0f430a02"
COMMAND_SET_MODE = f"{COMMAND_HEADER}0f4302"
COMMAND_GET_BASIC_INFO = f"{COMMAND_HEADER}000300"
COMMAND_SET_DRYING_FILTER = f"{COMMAND_TURN_ON}08"

MODES_COMMANDS = {
    HumidifierMode.HIGH: "010100",
    HumidifierMode.MEDIUM: "010200",
    HumidifierMode.LOW: "010300",
    HumidifierMode.QUIET: "010400",
    HumidifierMode.TARGET_HUMIDITY: "0200",
    HumidifierMode.SLEEP: "0300",
    HumidifierMode.AUTO: "040000",
}

DEVICE_GET_BASIC_SETTINGS_KEY = "570f4481"


class SwitchbotEvaporativeHumidifier(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Evaporative Humidifier"""

    _turn_on_command = COMMAND_TURN_ON
    _turn_off_command = f"{COMMAND_HEADER}0f430100"

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

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None

        _LOGGER.debug("basic info data: %s", _data.hex())
        isOn = bool(_data[1] & 0b10000000)
        mode = HumidifierMode(_data[1] & 0b00001111)
        over_humidify_protection = bool(_data[2] & 0b10000000)
        child_lock = bool(_data[2] & 0b00100000)
        tank_removed = bool(_data[2] & 0b00000100)
        tilted_alert = bool(_data[2] & 0b00000010)
        filter_missing = bool(_data[2] & 0b00000001)
        is_meter_binded = bool(_data[3] & 0b10000000)

        _temp_c, _temp_f, humidity = calculate_temperature_and_humidity(
            _data[3:6], is_meter_binded
        )

        water_level = HumidifierWaterLevel(_data[5] & 0b00000011).name.lower()
        filter_run_time = int.from_bytes(_data[6:8], byteorder="big") & 0xFFF
        target_humidity = _data[10] & 0b01111111

        return {
            "isOn": isOn,
            "mode": mode,
            "over_humidify_protection": over_humidify_protection,
            "child_lock": child_lock,
            "tank_removed": tank_removed,
            "tilted_alert": tilted_alert,
            "filter_missing": filter_missing,
            "is_meter_binded": is_meter_binded,
            "humidity": humidity,
            "temperature": _temp_c,
            "temp": {"c": _temp_c, "f": _temp_f},
            "water_level": water_level,
            "filter_run_time": filter_run_time,
            "target_humidity": target_humidity,
        }

    @update_after_operation
    async def set_target_humidity(self, target_humidity: int) -> bool:
        """Set target humidity."""
        self._validate_water_level()
        self._validate_mode_for_target_humidity()
        command = (
            COMMAND_SET_MODE
            + MODES_COMMANDS[self.get_mode()]
            + f"{target_humidity:02x}"
        )
        result = await self._send_command(command)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_mode(self, mode: HumidifierMode) -> bool:
        """Set device mode."""
        self._validate_water_level()
        self._validate_meter_binding(mode)

        if mode == HumidifierMode.DRYING_FILTER:
            command = COMMAND_SET_DRYING_FILTER
        else:
            command = COMMAND_SET_MODE + MODES_COMMANDS[mode]

        if mode in TARGET_HUMIDITY_MODES:
            target_humidity = self.get_target_humidity()
            if target_humidity is None:
                raise SwitchbotOperationError(
                    "Target humidity must be set before switching to target humidity mode or sleep mode"
                )
            command += f"{target_humidity:02x}"
        result = await self._send_command(command)
        return self._check_command_result(result, 0, {1})

    def _validate_water_level(self) -> None:
        """Validate that the water level is not empty."""
        if self.get_water_level() == HumidifierWaterLevel.EMPTY.name.lower():
            raise SwitchbotOperationError(
                "Cannot perform operation when water tank is empty"
            )

    def _validate_mode_for_target_humidity(self) -> None:
        """Validate that the current mode supports target humidity."""
        if self.get_mode() not in TARGET_HUMIDITY_MODES:
            raise SwitchbotOperationError(
                "Target humidity can only be set in target humidity mode or sleep mode"
            )

    def _validate_meter_binding(self, mode: HumidifierMode) -> None:
        """Validate that the meter is binded for specific modes."""
        if not self.is_meter_binded() and mode in [
            HumidifierMode.TARGET_HUMIDITY,
            HumidifierMode.AUTO,
        ]:
            raise SwitchbotOperationError(
                "Cannot set target humidity or auto mode when meter is not binded"
            )

    @update_after_operation
    async def set_child_lock(self, enabled: bool) -> bool:
        """Set child lock."""
        result = await self._send_command(
            COMMAND_CHILD_LOCK_ON if enabled else COMMAND_CHILD_LOCK_OFF
        )
        return self._check_command_result(result, 0, {1})

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

    def get_action(self) -> int:
        """Return current action from cache."""
        if not self.is_on():
            return HumidifierAction.OFF
        if self.get_mode() != HumidifierMode.DRYING_FILTER:
            return HumidifierAction.HUMIDIFYING
        return HumidifierAction.DRYING

    def is_meter_binded(self) -> bool | None:
        """Return meter bind state from cache."""
        return self._get_adv_value("is_meter_binded")
