from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import bot

from .test_adv_parser import generate_ble_device


def create_bot_for_command_testing(init_data: dict | None = None) -> bot.Switchbot:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = bot.Switchbot(ble_device, model=SwitchbotModel.BOT)
    device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock(return_value=True)
    device.update = AsyncMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice, init_data: dict | None = None
) -> SwitchBotAdvertisement:
    if init_data is None:
        init_data = {}
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"H\x10\xe1",
            "data": {"switchMode": False, "isOn": False, "battery": 97} | init_data,
            "model": "H",
            "isEncrypted": False,
            "modelFriendlyName": "Bot",
            "modelName": SwitchbotModel.BOT,
        },
        device=ble_device,
        rssi=-65,
        active=True,
    )


@pytest.mark.asyncio
async def test_turn_on_accepted_overrides_state() -> None:
    """Accepted command (e.g. 0x01 0x48 0x90) must update cached state to on."""
    device = create_bot_for_command_testing({"isOn": False})

    assert await device.turn_on() is True

    device._send_command.assert_called_with(bot.ON_KEY)
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off_accepted_overrides_state() -> None:
    """Accepted command must update cached state to off."""
    device = create_bot_for_command_testing({"isOn": True})

    assert await device.turn_off() is True

    device._send_command.assert_called_with(bot.OFF_KEY)
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_turn_on_rejected_preserves_state() -> None:
    """Rejected command (e.g. 0x03 0xff 0x00) must NOT override the cached state.

    Regression for sblibs/pySwitchbot#213: back-to-back presses where the bot
    silently ignores the second one would still flip HA's state to ``on``
    because ``_override_state`` ran unconditionally.
    """
    device = create_bot_for_command_testing({"isOn": False})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.turn_on() is False

    device._send_command.assert_called_with(bot.ON_KEY)
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_turn_off_rejected_preserves_state() -> None:
    """Rejected command must NOT override the cached state to off."""
    device = create_bot_for_command_testing({"isOn": True})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.turn_off() is False

    device._send_command.assert_called_with(bot.OFF_KEY)
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_inverse_mode_is_on_reflects_override() -> None:
    """is_on() must respect inverse_mode after a successful turn_on."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = bot.Switchbot(ble_device, model=SwitchbotModel.BOT, inverse_mode=True)
    device.update_from_advertisement(make_advertisement_data(ble_device, {"isOn": True}))
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock(return_value=True)
    device.update = AsyncMock()

    await device.turn_on()

    # inverse_mode flips the user-facing reading
    assert device.is_on() is False
