from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.const.fan import FanMode
from switchbot.devices import fan

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(init_data: dict | None = None):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    fan_device = fan.SwitchbotFan(ble_device)
    fan_device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    fan_device._send_command = AsyncMock()
    fan_device.update = AsyncMock()
    return fan_device


def make_advertisement_data(ble_device: BLEDevice, init_data: dict | None = None):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"~\x00R",
            "data": {
                "isOn": True,
                "mode": "NORMAL",
                "nightLight": 3,
                "oscillating": False,
                "battery": 60,
                "speed": 50,
            }
            | init_data,
            "isEncrypted": False,
            "model": ",",
            "modelFriendlyName": "Circulator Fan",
            "modelName": SwitchbotModel.CIRCULATOR_FAN,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response, expected",
    [
        (b"\x00", None),
        (b"\x07", None),
        (b"\x01\x02\x03", b"\x01\x02\x03"),
    ],
)
async def test__get_basic_info(response, expected):
    fan_device = create_device_for_command_testing()
    fan_device._send_command = AsyncMock(return_value=response)
    result = await fan_device._get_basic_info(cmd="TEST_CMD")
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "basic_info,firmware_info", [(True, False), (False, True), (False, False)]
)
async def test_get_basic_info_returns_none(basic_info, firmware_info):
    fan_device = create_device_for_command_testing()

    async def mock_get_basic_info(arg):
        if arg == fan.COMMAND_GET_BASIC_INFO:
            return basic_info
        elif arg == fan.DEVICE_GET_BASIC_SETTINGS_KEY:
            return firmware_info

    fan_device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    assert await fan_device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "basic_info,firmware_info,result",
    [
        (
            bytearray(b"\x01\x02W\x82g\xf5\xde4\x01=dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01W\x0b\x17\x01"),
            [87, True, False, "NORMAL", 61, 1.1],
        ),
        (
            bytearray(b"\x01\x02U\xc2g\xf5\xde4\x04+dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01U\x0b\x17\x01"),
            [85, True, True, "BABY", 43, 1.1],
        ),
    ],
)
async def test_get_basic_info(basic_info, firmware_info, result):
    fan_device = create_device_for_command_testing()

    async def mock_get_basic_info(arg):
        if arg == fan.COMMAND_GET_BASIC_INFO:
            return basic_info
        elif arg == fan.DEVICE_GET_BASIC_SETTINGS_KEY:
            return firmware_info

    fan_device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    info = await fan_device.get_basic_info()
    assert info["battery"] == result[0]
    assert info["isOn"] == result[1]
    assert info["oscillating"] == result[2]
    assert info["mode"] == result[3]
    assert info["speed"] == result[4]
    assert info["firmware"] == result[5]


@pytest.mark.asyncio
async def test_set_preset_mode():
    fan_device = create_device_for_command_testing({"mode": "BABY"})
    await fan_device.set_preset_mode("BABY")
    assert fan_device.get_current_mode() == "BABY"


@pytest.mark.asyncio
async def test_set_set_percentage_with_speed_is_0():
    fan_device = create_device_for_command_testing({"speed": 0, "isOn": False})
    await fan_device.turn_off()
    assert fan_device.get_current_percentage() == 0
    assert fan_device.is_on() is False


@pytest.mark.asyncio
async def test_set_set_percentage():
    fan_device = create_device_for_command_testing({"speed": 80})
    await fan_device.set_percentage(80)
    assert fan_device.get_current_percentage() == 80


@pytest.mark.asyncio
async def test_set_not_oscillation():
    fan_device = create_device_for_command_testing({"oscillating": False})
    await fan_device.set_oscillation(False)
    assert fan_device.get_oscillating_state() is False


@pytest.mark.asyncio
async def test_set_oscillation():
    fan_device = create_device_for_command_testing({"oscillating": True})
    await fan_device.set_oscillation(True)
    assert fan_device.get_oscillating_state() is True


@pytest.mark.asyncio
async def test_turn_on():
    fan_device = create_device_for_command_testing({"isOn": True})
    await fan_device.turn_on()
    assert fan_device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    fan_device = create_device_for_command_testing({"isOn": False})
    await fan_device.turn_off()
    assert fan_device.is_on() is False


def test_get_modes():
    assert FanMode.get_modes() == ["NORMAL", "NATURAL", "SLEEP", "BABY"]
