from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import plug

from .test_adv_parser import generate_ble_device


def create_plug_for_command_testing(
    init_data: dict | None = None,
) -> plug.SwitchbotPlugMini:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = plug.SwitchbotPlugMini(ble_device, model=SwitchbotModel.PLUG_MINI)
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
            "rawAdvData": b"g\x00\x00",
            "data": {"switchMode": True, "isOn": False, "wattage": 0} | init_data,
            "model": "g",
            "isEncrypted": False,
            "modelFriendlyName": "Plug Mini",
            "modelName": SwitchbotModel.PLUG_MINI,
        },
        device=ble_device,
        rssi=-65,
        active=True,
    )


@pytest.mark.asyncio
async def test_turn_on_accepted_overrides_state() -> None:
    """Accepted command must update cached state to on."""
    device = create_plug_for_command_testing({"isOn": False})

    assert await device.turn_on() is True

    device._send_command.assert_awaited_once_with(plug.PLUG_ON_KEY)
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off_accepted_overrides_state() -> None:
    """Accepted command must update cached state to off."""
    device = create_plug_for_command_testing({"isOn": True})

    assert await device.turn_off() is True

    device._send_command.assert_awaited_once_with(plug.PLUG_OFF_KEY)
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_turn_on_rejected_preserves_state() -> None:
    """Rejected command must NOT override the cached state."""
    device = create_plug_for_command_testing({"isOn": False})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.turn_on() is False

    device._send_command.assert_awaited_once_with(plug.PLUG_ON_KEY)
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_turn_off_rejected_preserves_state() -> None:
    """Rejected command must NOT override the cached state to off."""
    device = create_plug_for_command_testing({"isOn": True})
    device._check_command_result = MagicMock(return_value=False)

    assert await device.turn_off() is False

    device._send_command.assert_awaited_once_with(plug.PLUG_OFF_KEY)
    assert device.is_on() is True
