from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.const.light import ColorMode
from switchbot.devices import ceiling_light

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    init_data: dict | None = None, model: SwitchbotModel = SwitchbotModel.CEILING_LIGHT
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = ceiling_light.SwitchbotCeilingLight(ble_device, model=model)
    device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(ble_device: BLEDevice, init_data: dict | None = None):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"q\x00",
            "data": {
                "brightness": 1,
                "color_mode": 1,
                "cw": 6387,
                "isOn": False,
                "sequence_number": 10,
            }
            | init_data,
            "isEncrypted": False,
            "model": b"q\x00",
            "modelFriendlyName": "Ceiling Light",
            "modelName": SwitchbotModel.CEILING_LIGHT,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_default_info():
    """Test default initialization of the ceiling light."""
    device = create_device_for_command_testing()

    assert device.rgb is None

    device._state = {"cw": 3200}

    assert device.is_on() is False
    assert device.on is False
    assert device.color_mode == ColorMode.COLOR_TEMP
    assert device.color_modes == {ColorMode.COLOR_TEMP}
    assert device.color_temp == 3200
    assert device.brightness == 1
    assert device.min_temp == 2700
    assert device.max_temp == 6500
    assert device.get_effect_list is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "version_info"), [(True, False), (False, True), (False, False)]
)
async def test_get_basic_info_returns_none(basic_info, version_info):
    device = create_device_for_command_testing()

    async def mock_get_basic_info(arg):
        if arg == device._get_basic_info_command[1]:
            return basic_info
        if arg == device._get_basic_info_command[0]:
            return version_info
        return None

    device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("info_data", "result"),
    [
        (
            {
                "basic_info": b"\x01\x80=\x0f\xa1\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [True, 61, 4001, 0, 2.1],
        ),
        (
            {
                "basic_info": b"\x01\x80\x0e\x12B\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [True, 14, 4674, 0, 2.1],
        ),
        (
            {
                "basic_info": b"\x01\x00\x0e\x10\x96\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [False, 14, 4246, 0, 2.1],
        ),
    ],
)
async def test_get_basic_info(info_data, result):
    """Test getting basic info from the ceiling light."""
    device = create_device_for_command_testing()

    async def mock_get_basic_info(args: str) -> list[int] | None:
        if args == device._get_basic_info_command[1]:
            return info_data["basic_info"]
        if args == device._get_basic_info_command[0]:
            return info_data["version_info"]
        return None

    device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)
    info = await device.get_basic_info()

    assert info["isOn"] is result[0]
    assert info["brightness"] == result[1]
    assert info["cw"] == result[2]
    assert info["color_mode"] == result[3]
    assert info["firmware"] == result[4]


@pytest.mark.asyncio
async def test_set_color_temp():
    """Test setting color temperature."""
    device = create_device_for_command_testing()

    await device.set_color_temp(50, 3000)

    device._send_command.assert_called_with(
        device._set_color_temp_command.format("320BB8")
    )


@pytest.mark.asyncio
async def test_turn_on():
    """Test turning on the ceiling light."""
    device = create_device_for_command_testing({"isOn": True})

    await device.turn_on()

    device._send_command.assert_called_with(device._turn_on_command)

    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    """Test turning off the ceiling light."""
    device = create_device_for_command_testing({"isOn": False})

    await device.turn_off()

    device._send_command.assert_called_with(device._turn_off_command)

    assert device.is_on() is False


@pytest.mark.asyncio
async def test_set_brightness():
    """Test setting brightness."""
    device = create_device_for_command_testing()

    await device.set_brightness(75)

    device._send_command.assert_called_with(
        device._set_brightness_command.format("4B0FA1")
    )
