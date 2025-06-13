import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..helpers import parse_power_data, parse_uint24_be
from ..models import SwitchBotAdvertisement
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)

# Bit masks for status parsing
SWITCH1_ON_MASK = 0b10000000
SWITCH2_ON_MASK = 0b01000000
DOOR_OPEN_MASK = 0b00100000

COMMAND_HEADER = "57"
COMMAND_CONTROL = "570f70"
COMMAND_TOGGLE = f"{COMMAND_CONTROL}010200"
COMMAND_GET_VOLTAGE_AND_CURRENT = f"{COMMAND_HEADER}0f7106000000"

COMMAND_GET_BASIC_INFO = f"{COMMAND_HEADER}0f7181"
COMMAND_GET_CHANNEL1_INFO = f"{COMMAND_HEADER}0f710600{{}}{{}}"
COMMAND_GET_CHANNEL2_INFO = f"{COMMAND_HEADER}0f710601{{}}{{}}"


MULTI_CHANNEL_COMMANDS_TURN_ON = {
    SwitchbotModel.RELAY_SWITCH_2PM: {
        1: "570f70010d00",
        2: "570f70010700",
    }
}
MULTI_CHANNEL_COMMANDS_TURN_OFF = {
    SwitchbotModel.RELAY_SWITCH_2PM: {
        1: "570f70010c00",
        2: "570f70010300",
    }
}
MULTI_CHANNEL_COMMANDS_TOGGLE = {
    SwitchbotModel.RELAY_SWITCH_2PM: {
        1: "570f70010e00",
        2: "570f70010b00",
    }
}
MULTI_CHANNEL_COMMANDS_GET_VOLTAGE_AND_CURRENT = {
    SwitchbotModel.RELAY_SWITCH_2PM: {
        1: COMMAND_GET_CHANNEL1_INFO,
        2: COMMAND_GET_CHANNEL2_INFO,
    }
}


class SwitchbotRelaySwitch(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot relay switch 1pm."""

    _turn_on_command = f"{COMMAND_CONTROL}010100"
    _turn_off_command = f"{COMMAND_CONTROL}010000"

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.RELAY_SWITCH_1PM,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.RELAY_SWITCH_1PM,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    def _reset_power_data(self, data: dict[str, Any]) -> None:
        """Reset power-related data to 0."""
        for key in ["power", "current", "voltage"]:
            data[key] = 0

    def _parse_common_data(self, raw_data: bytes) -> dict[str, Any]:
        """Parse common data from raw bytes."""
        return {
            "sequence_number": raw_data[1],
            "isOn": bool(raw_data[2] & SWITCH1_ON_MASK),
            "firmware": raw_data[16] / 10.0,
            "channel2_isOn": bool(raw_data[2] & SWITCH2_ON_MASK),
        }

    def _parse_user_data(self, raw_data: bytes) -> dict[str, Any]:
        """Parse user-specific data from raw bytes."""
        _energy = parse_uint24_be(raw_data, 1) / 60000
        _energy_usage_yesterday = parse_uint24_be(raw_data, 4) / 60000
        _use_time = parse_power_data(raw_data, 7, 60.0)
        _voltage = parse_power_data(raw_data, 9, 10.0)
        _current = parse_power_data(raw_data, 11, 1000.0)
        _power = parse_power_data(raw_data, 13, 10.0)

        return {
            "energy": 0.01 if 0 < _energy <= 0.01 else round(_energy, 2),
            "energy usage yesterday": 0.01
            if 0 < _energy_usage_yesterday <= 0.01
            else round(_energy_usage_yesterday, 2),
            "use_time": round(_use_time, 1),
            "voltage": 0.1 if 0 < _voltage <= 0.1 else round(_voltage),
            "current": 0.1 if 0 < _current <= 0.1 else round(_current, 1),
            "power": 0.1 if 0 < _power <= 0.1 else round(_power, 1),
        }

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        adv_data = advertisement.data["data"]
        channel = self._channel if hasattr(self, "_channel") else None

        if self._model in (
            SwitchbotModel.RELAY_SWITCH_1PM,
            SwitchbotModel.RELAY_SWITCH_2PM,
        ):
            if channel is None:
                adv_data["voltage"] = self._get_adv_value("voltage") or 0
                adv_data["current"] = self._get_adv_value("current") or 0
                adv_data["power"] = self._get_adv_value("power") or 0
                adv_data["energy"] = self._get_adv_value("energy") or 0
            else:
                for i in range(1, channel + 1):
                    adv_data[i] = adv_data.get(i, {})
                    adv_data[i]["voltage"] = self._get_adv_value("voltage", i) or 0
                    adv_data[i]["current"] = self._get_adv_value("current", i) or 0
                    adv_data[i]["power"] = self._get_adv_value("power", i) or 0
                    adv_data[i]["energy"] = self._get_adv_value("energy", i) or 0
        super().update_from_advertisement(advertisement)

    def get_current_time_and_start_time(self) -> int:
        """Get current time in seconds since epoch."""
        current_time = int(time.time())
        current_time_hex = f"{current_time:08x}"
        current_day_start_time = int(current_time / 86400) * 86400
        current_day_start_time_hex = f"{current_day_start_time:08x}"

        return current_time_hex, current_day_start_time_hex

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        current_time_hex, current_day_start_time_hex = (
            self.get_current_time_and_start_time()
        )

        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (
            _channel1_data := await self._get_basic_info(
                COMMAND_GET_CHANNEL1_INFO.format(
                    current_time_hex, current_day_start_time_hex
                )
            )
        ):
            return None

        _LOGGER.debug(
            "on-off hex: %s, channel1_hex_data: %s", _data.hex(), _channel1_data.hex()
        )

        common_data = self._parse_common_data(_data)
        user_data = self._parse_user_data(_channel1_data)

        if self._model in (
            SwitchbotModel.RELAY_SWITCH_1,
            SwitchbotModel.GARAGE_DOOR_OPENER,
        ):
            for key in ["voltage", "current", "power", "energy"]:
                user_data.pop(key, None)

        if not common_data["isOn"]:
            self._reset_power_data(user_data)

        garage_door_opener_data = {"door_open": not bool(_data[2] & DOOR_OPEN_MASK)}

        _LOGGER.debug("common_data: %s, user_data: %s", common_data, user_data)

        if self._model == SwitchbotModel.GARAGE_DOOR_OPENER:
            return common_data | garage_door_opener_data
        return common_data | user_data

    @update_after_operation
    async def async_toggle(self, **kwargs) -> bool:
        """Toggle device."""
        result = await self._send_command(COMMAND_TOGGLE)
        return self._check_command_result(result, 0, {1})

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn")


class SwitchbotRelaySwitch2PM(SwitchbotRelaySwitch):
    """Representation of a Switchbot relay switch 2pm."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.RELAY_SWITCH_2PM,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, interface, model, **kwargs)
        self._channel = 2

    @property
    def channel(self) -> int:
        return self._channel

    def get_parsed_data(self, channel: int | None = None) -> dict[str, Any]:
        """Return parsed device data, optionally for a specific channel."""
        data = self.data.get("data") or {}
        return data.get(channel, {})

    async def get_basic_info(self):
        current_time_hex, current_day_start_time_hex = (
            self.get_current_time_and_start_time()
        )
        if not (common_data := await super().get_basic_info()):
            return None
        if not (
            _channel2_data := await self._get_basic_info(
                COMMAND_GET_CHANNEL2_INFO.format(
                    current_time_hex, current_day_start_time_hex
                )
            )
        ):
            return None

        _LOGGER.debug("channel2_hex_data: %s", _channel2_data.hex())

        channel2_data = self._parse_user_data(_channel2_data)
        channel2_data["isOn"] = common_data["channel2_isOn"]

        if not channel2_data["isOn"]:
            self._reset_power_data(channel2_data)

        _LOGGER.debug(
            "channel1_data: %s, channel2_data: %s", common_data, channel2_data
        )
        return {1: common_data, 2: channel2_data}

    @update_after_operation
    async def turn_on(self, channel: int) -> bool:
        """Turn device on."""
        result = await self._send_command(
            MULTI_CHANNEL_COMMANDS_TURN_ON[self._model][channel]
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self, channel: int) -> bool:
        """Turn device off."""
        result = await self._send_command(
            MULTI_CHANNEL_COMMANDS_TURN_OFF[self._model][channel]
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def async_toggle(self, channel: int) -> bool:
        """Toggle device."""
        result = await self._send_command(
            MULTI_CHANNEL_COMMANDS_TOGGLE[self._model][channel]
        )
        return self._check_command_result(result, 0, {1})

    def is_on(self, channel: int) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn", channel)

    def switch_mode(self, channel: int) -> bool | None:
        """Return true or false from cache."""
        return self._get_adv_value("switchMode", channel)
