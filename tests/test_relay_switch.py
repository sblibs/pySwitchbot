from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import relay_switch

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    rawAdvData: bytes, model: str, init_data: dict | None = None):
    """Create a device for command testing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device_class = (
        relay_switch.SwitchbotRelaySwitch2PM
        if model == SwitchbotModel.RELAY_SWITCH_2PM
        else relay_switch.SwitchbotRelaySwitch
    )
    device = device_class(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff"
    )
    device.update_from_advertisement(
        make_advertisement_data(ble_device, rawAdvData, model, init_data)
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device

def make_advertisement_data(
    ble_device: BLEDevice, rawAdvData: bytes, model: str, init_data: dict | None = None
):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}
    if model == SwitchbotModel.RELAY_SWITCH_2PM:
        return SwitchBotAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            data={
                "rawAdvData": rawAdvData,
                "data": {
                    1: {
                        "switchMode": True,
                        "sequence_number": 99,
                        "isOn": True,
                    },
                    2: {
                        "switchMode": True,
                        "sequence_number": 99,
                        "isOn": False,
                    },
                }
                | init_data,
                "isEncrypted": False,
                "model": model,
                "modelFriendlyName": "Relay Switch 2PM",
                "modelName": SwitchbotModel.RELAY_SWITCH_2PM,
            },
            device=ble_device,
            rssi=-80,
            active=True,
        )
    return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "init_data"),
    [
        (
            b"\x00\x00\x00\x00\x00\x00",
            SwitchbotModel.RELAY_SWITCH_2PM,
            {1: {"isOn": True}, 2: {"isOn": True}},
        ),
    ],
)
async def test_turn_on_2PM(rawAdvData, model, init_data):
    """Test turn on command."""
    device = create_device_for_command_testing(rawAdvData, model, init_data)
    await device.turn_on(1)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_ON[model][1]
    )
    assert device.is_on(1) is True

    await device.turn_on(2)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_ON[model][2]
    )
    assert device.is_on(2) is True

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "init_data"),
    [
        (
            b"\x00\x00\x00\x00\x00\x00",
            SwitchbotModel.RELAY_SWITCH_2PM,
            {1: {"isOn": False}, 2: {"isOn": False}},
        ),
    ],
)
async def test_turn_off_2PM(rawAdvData, model, init_data):
    """Test turn off command."""
    device = create_device_for_command_testing(rawAdvData, model, init_data)
    await device.turn_off(1)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_OFF[model][1]
    )
    assert device.is_on(1) is False

    await device.turn_off(2)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_OFF[model][2]
    )
    assert device.is_on(2) is False

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    [
        (
            b"\x00\x00\x00\x00\x00\x00",
            SwitchbotModel.RELAY_SWITCH_2PM,
        ),
    ],
)
async def test_turn_toggle_2PM(rawAdvData, model):
    """Test toggle command."""
    device = create_device_for_command_testing(rawAdvData, model)
    await device.async_toggle(1)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TOGGLE[model][1]
    )
    assert device.is_on(1) is True

    await device.async_toggle(2)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TOGGLE[model][2]
    )
    assert device.is_on(2) is False

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    [
        (
            b"\x00\x00\x00\x00\x00\x00",
            SwitchbotModel.RELAY_SWITCH_2PM,
        ),
    ],
)
async def test_get_switch_mode_2PM(rawAdvData, model):
    """Test get switch mode."""
    device = create_device_for_command_testing(rawAdvData, model)
    assert device.switch_mode(1) is True
    assert device.switch_mode(2) is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    [
        (
            b"\x00\x00\x00\x00\x00\x00",
            SwitchbotModel.RELAY_SWITCH_2PM,
        ),
    ],
)
@pytest.mark.parametrize(
    ("channel1_info", "channel2_info"), [(True, False), (False, True), (False, False)]
)
async def test_get_basic_info_returns_none(rawAdvData, model, channel1_info, channel2_info):
    device = create_device_for_command_testing(rawAdvData, model)

    device.get_current_time_and_start_time = MagicMock(return_value=("683074d6", "682fba80"))


