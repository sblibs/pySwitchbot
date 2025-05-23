import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..models import SwitchBotAdvertisement
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)

COMMAND_HEADER = "57"
COMMAND_TURN_OFF = f"{COMMAND_HEADER}0f70010000"
COMMAND_TURN_ON = f"{COMMAND_HEADER}0f70010100"
COMMAND_TOGGLE = f"{COMMAND_HEADER}0f70010200"
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

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        adv_data = advertisement.data["data"]
        channel = self._channel if hasattr(self, "_channel") else None

        if channel is None:
            adv_data["voltage"] = self._get_adv_value("voltage") or 0
            adv_data["current"] = self._get_adv_value("current") or 0
        else:
            for i in range(1, channel + 1):
                adv_data[i] = adv_data.get(i, {})
                adv_data[i]["voltage"] = self._get_adv_value("voltage", i) or 0
                adv_data[i]["current"] = self._get_adv_value("current", i) or 0
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
        current_time_hex, current_day_start_time_hex = self.get_current_time_and_start_time()

        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (_channel1_data := await self._get_basic_info(COMMAND_GET_CHANNEL1_INFO.format(current_time_hex, current_day_start_time_hex))):
            return None

        common_data = {
            "isOn": bool(_data[2] & 0b10000000),
            "firmware": _data[16] / 10.0,
            "use_time": int.from_bytes(_channel1_data[7:9], "big"),

        }

        user_data = {
            "Electricity Usage Today": int.from_bytes(_channel1_data[1:4], "big"),
            "Electricity Usage Yesterday": int.from_bytes(_channel1_data[4:7], "big"),
            "voltage": int.from_bytes(_channel1_data[9:11], "big") / 10.0,
            "current": int.from_bytes(_channel1_data[11:13], "big"),
            "power": int.from_bytes(_channel1_data[13:15], "big") / 10.0,
        }

        garage_door_opener_data = {
            "door_open": not bool(_data[7] & 0b00100000),
        }

        _LOGGER.debug("common_data: %s, garage_door_opener_data: %s", common_data, garage_door_opener_data)

        if self._model == SwitchbotModel.RELAY_SWITCH_1:
            return common_data
        if self._model == SwitchbotModel.GARAGE_DOOR_OPENER:
            return common_data | garage_door_opener_data
        return common_data | user_data

    @update_after_operation
    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(COMMAND_TURN_ON)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(COMMAND_TURN_OFF)
        return self._check_command_result(result, 0, {1})

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
        current_time_hex, current_day_start_time_hex = self.get_current_time_and_start_time()
        if not (common_data := await super().get_basic_info()):
            return None
        if not (
                _channel2_data := await self._get_basic_info(COMMAND_GET_CHANNEL2_INFO.format(current_time_hex, current_day_start_time_hex))
            ):
            return None


        result = {
            1: common_data,
            2: {
                "isOn": bool(_channel2_data[2] & 0b01000000),
                "Electricity Usage Today": int.from_bytes(_channel2_data[1:4], "big"),
                "Electricity Usage Yesterday": int.from_bytes(_channel2_data[4:7], "big"),
                "use_time": int.from_bytes(_channel2_data[7:9], "big"),
                "voltage": int.from_bytes(_channel2_data[9:11], "big") / 10.0,
                "current": int.from_bytes(_channel2_data[11:13], "big"),
                "power": int.from_bytes(_channel2_data[13:15], "big") / 10.0,
            }
        }

        _LOGGER.debug("Multi channel basic info: %s", result)

        return result

    @update_after_operation
    async def turn_on(self, channel: int) -> bool:
        """Turn device on."""
        result = await self._send_command(MULTI_CHANNEL_COMMANDS_TURN_ON[self._model][channel])
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off(self, channel: int) -> bool:
        """Turn device off."""
        result = await self._send_command(MULTI_CHANNEL_COMMANDS_TURN_OFF[self._model][channel])
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def async_toggle(self, channel: int) -> bool:
        """Toggle device."""
        result = await self._send_command(MULTI_CHANNEL_COMMANDS_TOGGLE[self._model][channel])
        return self._check_command_result(result, 0, {1})

    def is_on(self, channel: int) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn", channel)

    def switch_mode(self, channel: int) -> bool | None:
        """Return true or false from cache."""
        return self._get_adv_value("switchMode", channel)
