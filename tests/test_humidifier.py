from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import humidifier

from .test_adv_parser import generate_ble_device


def create_humidifier_for_command_testing(
    init_data: dict | None = None,
) -> humidifier.SwitchbotHumidifier:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = humidifier.SwitchbotHumidifier(ble_device, model=SwitchbotModel.HUMIDIFIER)
    device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock(return_value=True)
    return device


def make_advertisement_data(
    ble_device: BLEDevice, init_data: dict | None = None
) -> SwitchBotAdvertisement:
    if init_data is None:
        init_data = {}
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"e\x00\x00",
            "data": {"isOn": False, "level": 50} | init_data,
            "model": "e",
            "isEncrypted": False,
            "modelFriendlyName": "Humidifier",
            "modelName": SwitchbotModel.HUMIDIFIER,
        },
        device=ble_device,
        rssi=-65,
        active=True,
    )


@pytest.mark.asyncio
async def test_turn_on_accepted_overrides_state() -> None:
    """Accepted command must update cached state to on."""
    device = create_humidifier_for_command_testing({"isOn": False, "level": 50})

    assert await device.turn_on() is True

    device._send_command.assert_awaited_once()
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off_accepted_overrides_state() -> None:
    """Accepted command must update cached state to off."""
    device = create_humidifier_for_command_testing({"isOn": True, "level": 50})

    assert await device.turn_off() is True

    device._send_command.assert_awaited_once()
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_turn_on_rejected_preserves_state() -> None:
    """Rejected command must NOT flip cached isOn to True."""
    device = create_humidifier_for_command_testing({"isOn": False, "level": 50})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.turn_on() is False

    device._send_command.assert_awaited_once()
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_turn_off_rejected_preserves_state() -> None:
    """Rejected command must NOT flip cached isOn to False."""
    device = create_humidifier_for_command_testing({"isOn": True, "level": 50})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.turn_off() is False

    device._send_command.assert_awaited_once()
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_set_level_accepted_overrides_state() -> None:
    """Accepted set_level must update cached level."""
    device = create_humidifier_for_command_testing({"isOn": True, "level": 33})

    assert await device.set_level(66) is True

    device._send_command.assert_awaited_once()
    assert device.get_level() == 66


@pytest.mark.asyncio
async def test_set_level_rejected_preserves_state() -> None:
    """Rejected set_level must NOT update cached level."""
    device = create_humidifier_for_command_testing({"isOn": True, "level": 33})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.set_level(66) is False

    device._send_command.assert_awaited_once()
    assert device.get_level() == 33
