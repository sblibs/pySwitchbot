from unittest.mock import AsyncMock, Mock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import (
    SwitchBotAdvertisement,
    SwitchbotModel,
    SwitchbotOperationError,
)
from switchbot.devices import bot

from .test_adv_parser import generate_ble_device


def make_advertisement_data(
    ble_device: BLEDevice,
) -> SwitchBotAdvertisement:
    """Create Bot advertisement data for tests."""
    data: dict[str, bool | int | None] = {
        "battery": 89,
        "isOn": True,
        "switchMode": True,
    }
    return SwitchBotAdvertisement(
        address=ble_device.address,
        data={
            "rawAdvData": b"H\x90\xd9",
            "data": data,
            "isEncrypted": False,
            "model": "H",
            "modelFriendlyName": "Bot",
            "modelName": SwitchbotModel.BOT,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def create_device_for_command_testing(
    *,
    inverse_direction: bool | None = None,
) -> bot.Switchbot:
    """Create a Bot device with mocked Bluetooth commands."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "WoHand")
    device = bot.Switchbot(ble_device)
    device.update_from_advertisement(make_advertisement_data(ble_device))
    if inverse_direction is not None:
        device._update_parsed_data({"inverseDirection": inverse_direction})
    device._send_command = AsyncMock(return_value=b"\x01")
    device.update = AsyncMock()
    return device


@pytest.mark.asyncio
async def test_update_reads_inverse_direction() -> None:
    """Test updating reads inverse direction."""
    device = create_device_for_command_testing()
    device.update = bot.Switchbot.update.__get__(device)
    device._get_basic_info = AsyncMock(
        return_value=bytes([1, 89, 31, 75, 0, 0, 0, 0, 2, 17, 0])
    )

    await device.update()

    assert device.inverse_direction() is True
    assert device.parsed_data["strength"] == 75


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("inverse_direction", "expected_command"),
    [(False, "57034b10"), (True, "57034b11")],
)
async def test_set_inverse_direction_preserves_mode_and_strength(
    inverse_direction: bool,
    expected_command: str,
) -> None:
    """Test changing inverse direction preserves the current Bot settings."""
    device = create_device_for_command_testing()
    device.get_basic_info = AsyncMock(
        return_value={
            "battery": 89,
            "firmware": 3.1,
            "strength": 75,
            "timers": 2,
            "switchMode": True,
            "inverseDirection": False,
            "holdSeconds": 0,
        }
    )
    assert await device.set_inverse_direction(inverse_direction) is True

    device._send_command.assert_awaited_once_with(expected_command)


@pytest.mark.asyncio
async def test_set_inverse_direction_raises_when_settings_unavailable() -> None:
    """Test changing inverse direction fails if current settings cannot be read."""
    device = create_device_for_command_testing()
    device.get_basic_info = AsyncMock(return_value=None)

    with pytest.raises(
        SwitchbotOperationError, match="Unable to get current Bot mode settings"
    ):
        await device.set_inverse_direction(True)


@pytest.mark.asyncio
async def test_set_inverse_direction_returns_false_for_rejected_command() -> None:
    """Test a rejected inverse direction command does not update the cache."""
    device = create_device_for_command_testing(inverse_direction=False)
    device.get_basic_info = AsyncMock(
        return_value={
            "switchMode": True,
            "strength": 75,
        }
    )
    device._send_command = AsyncMock(return_value=b"\x00")

    assert await device.set_inverse_direction(True) is False
    assert device.inverse_direction() is False


@pytest.mark.asyncio
async def test_set_switch_mode_uses_confirmed_settings() -> None:
    """Test setting switch mode caches the settings read back from the Bot."""
    device = create_device_for_command_testing(inverse_direction=False)
    device.update = bot.Switchbot.update.__get__(device)
    device._send_command = AsyncMock(
        side_effect=[
            b"\x01",
            bytes([1, 89, 31, 75, 0, 0, 0, 0, 2, 17, 0]),
        ]
    )
    callback = Mock()
    device.subscribe(callback)

    assert await device.set_switch_mode(
        switch_mode=True,
        strength=75,
        inverse=True,
    )

    assert device.switch_mode() is True
    assert device.inverse_direction() is True
    assert device.parsed_data["strength"] == 75
    assert device._send_command.await_args_list[0].args == ("57034b11",)
    callback.assert_called_once_with()
