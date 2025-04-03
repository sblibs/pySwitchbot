from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import roller_shade

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    position=50, calibration=True, reverse_mode=False
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    roller_shade_device = roller_shade.SwitchbotRollerShade(
        ble_device, reverse_mode=reverse_mode
    )
    roller_shade_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, position, calibration)
    )
    roller_shade_device._send_multiple_commands = AsyncMock()
    roller_shade_device.update = AsyncMock()
    return roller_shade_device


def make_advertisement_data(
    ble_device: BLEDevice, in_motion: bool, position: int, calibration: bool = True
):
    """Set advertisement data with defaults."""
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b",\x00'\x9f\x11\x04",
            "data": {
                "battery": 39,
                "calibration": calibration,
                "deviceChain": 1,
                "inMotion": in_motion,
                "lightLevel": 1,
                "position": position,
            },
            "isEncrypted": False,
            "model": ",",
            "modelFriendlyName": "Roller Shade",
            "modelName": SwitchbotModel.ROLLER_SHADE,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_open():
    roller_shade_device = create_device_for_command_testing()
    await roller_shade_device.open()
    assert roller_shade_device.is_opening() is True
    assert roller_shade_device.is_closing() is False
    roller_shade_device._send_multiple_commands.assert_awaited_once_with(
        roller_shade.OPEN_KEYS
    )


@pytest.mark.asyncio
async def test_close():
    roller_shade_device = create_device_for_command_testing()
    await roller_shade_device.close()
    assert roller_shade_device.is_opening() is False
    assert roller_shade_device.is_closing() is True
    roller_shade_device._send_multiple_commands.assert_awaited_once_with(
        roller_shade.CLOSE_KEYS
    )


@pytest.mark.asyncio
async def test_get_basic_info_returns_none_when_no_data():
    roller_shade_device = create_device_for_command_testing()
    roller_shade_device._get_basic_info = AsyncMock(return_value=None)

    assert await roller_shade_device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reverse_mode,data,result",
    [
        (
            True,
            bytes([0, 1, 10, 2, 0, 50, 4]),
            [1, 1, 2, "anticlockwise", False, False, False, False, False, 50, 4],
        ),
        (
            True,
            bytes([0, 1, 10, 2, 214, 50, 4]),
            [1, 1, 2, "clockwise", True, False, True, True, True, 50, 4],
        ),
    ],
)
async def test_get_basic_info(reverse_mode, data, result):
    blind_device = create_device_for_command_testing(reverse_mode=reverse_mode)
    blind_device._get_basic_info = AsyncMock(return_value=data)

    info = await blind_device.get_basic_info()
    assert info["battery"] == result[0]
    assert info["firmware"] == result[1]
    assert info["chainLength"] == result[2]
    assert info["openDirection"] == result[3]
    assert info["fault"] == result[4]
    assert info["solarPanel"] == result[5]
    assert info["calibration"] == result[6]
    assert info["calibrated"] == result[7]
    assert info["inMotion"] == result[8]
    assert info["position"] == result[9]
    assert info["timers"] == result[10]


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing(reverse_mode):
    """Test passive closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = roller_shade.SwitchbotRollerShade(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening_then_stop(reverse_mode):
    """Test passive stopped after opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = roller_shade.SwitchbotRollerShade(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 10)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 10)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing_then_stop(reverse_mode):
    """Test passive stopped after closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = roller_shade.SwitchbotRollerShade(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 90)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
async def test_stop():
    curtain_device = create_device_for_command_testing()
    await curtain_device.stop()
    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False
    curtain_device._send_multiple_commands.assert_awaited_once_with(
        roller_shade.STOP_KEYS
    )


@pytest.mark.asyncio
async def test_set_position_opening():
    curtain_device = create_device_for_command_testing(reverse_mode=True)
    await curtain_device.set_position(0)
    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False
    curtain_device._send_multiple_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_position_closing():
    curtain_device = create_device_for_command_testing(reverse_mode=True)
    await curtain_device.set_position(100)
    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True
    curtain_device._send_multiple_commands.assert_awaited_once()


def test_get_position():
    curtain_device = create_device_for_command_testing()
    assert curtain_device.get_position() == 50


def test_update_motion_direction_with_no_previous_position():
    curtain_device = create_device_for_command_testing(reverse_mode=True)
    curtain_device._update_motion_direction(True, None, 100)
    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


def test_update_motion_direction_with_previous_position():
    curtain_device = create_device_for_command_testing(reverse_mode=True)
    curtain_device._update_motion_direction(True, 50, 100)
    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False
