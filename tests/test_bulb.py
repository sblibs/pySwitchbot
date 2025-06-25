from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.const.light import ColorMode
from switchbot.devices import bulb
from switchbot.devices.device import SwitchbotOperationError

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    init_data: dict | None = None, model: SwitchbotModel = SwitchbotModel.COLOR_BULB
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = bulb.SwitchbotBulb(ble_device, model=model)
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
            "rawAdvData": b"u\x00d",
            "data": {
                "brightness": 1,
                "color_mode": 2,
                "delay": False,
                "isOn": True,
                "loop_index": 0,
                "preset": False,
                "sequence_number": 2,
                "speed": 0,
            }
            | init_data,
            "isEncrypted": False,
            "model": "u",
            "modelFriendlyName": "Color Bulb",
            "modelName": SwitchbotModel.COLOR_BULB,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_default_info():
    """Test default initialization of the color bulb."""
    device = create_device_for_command_testing()

    assert device.rgb is None

    device._state = {"r": 30, "g": 0, "b": 0, "cw": 3200}

    assert device.is_on() is True
    assert device.on is True
    assert device.color_mode == ColorMode.RGB
    assert device.color_modes == {ColorMode.RGB, ColorMode.COLOR_TEMP}
    assert device.rgb == (30, 0, 0)
    assert device.color_temp == 3200
    assert device.brightness == 1
    assert device.min_temp == 2700
    assert device.max_temp == 6500
    assert device.get_effect_list == ["colorful", "flickering", "breathing"]


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
                "basic_info": b"\x01\x80\x01\xff\x91\x96\x00\x00\xff\xff\x02",
                "version_info": b"\x01\x01\x11",
            },
            [True, 1, 255, 145, 150, 0, 2, 1.7],
        ),
        (
            {
                "basic_info": b"\x01\x80;\x00\x00\x00\x0c\x99\xff\xff\x01",
                "version_info": b"\x01\x01\x11",
            },
            [True, 59, 0, 0, 0, 3225, 1, 1.7],
        ),
        (
            {
                "basic_info": b"\x01\x80\t!7\xff\x00\x00\xff\xff\x02",
                "version_info": b"\x01\x01\x11",
            },
            [True, 9, 33, 55, 255, 0, 2, 1.7],
        ),
    ],
)
async def test_get_basic_info(info_data, result):
    """Test getting basic info from the color bulb."""
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
    assert info["r"] == result[2]
    assert info["g"] == result[3]
    assert info["b"] == result[4]
    assert info["cw"] == result[5]
    assert info["color_mode"] == result[6]
    assert info["firmware"] == result[7]


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
    """Test turning on the color bulb."""
    device = create_device_for_command_testing({"isOn": True})

    await device.turn_on()

    device._send_command.assert_called_with(device._turn_on_command)

    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    """Test turning off the color bulb."""
    device = create_device_for_command_testing({"isOn": False})

    await device.turn_off()

    device._send_command.assert_called_with(device._turn_off_command)

    assert device.is_on() is False


@pytest.mark.asyncio
async def test_set_brightness():
    """Test setting brightness."""
    device = create_device_for_command_testing()

    await device.set_brightness(75)

    device._send_command.assert_called_with(device._set_brightness_command.format("4B"))


@pytest.mark.asyncio
async def test_set_rgb():
    """Test setting RGB values."""
    device = create_device_for_command_testing()

    await device.set_rgb(100, 255, 128, 64)

    device._send_command.assert_called_with(device._set_rgb_command.format("64FF8040"))


@pytest.mark.asyncio
async def test_set_effect_with_invalid_effect():
    """Test setting an invalid effect."""
    device = create_device_for_command_testing()

    with pytest.raises(
        SwitchbotOperationError, match="Effect invalid_effect not supported"
    ):
        await device.set_effect("invalid_effect")


@pytest.mark.asyncio
async def test_set_effect_with_valid_effect():
    """Test setting a valid effect."""
    device = create_device_for_command_testing()

    await device.set_effect("colorful")

    device._send_command.assert_called_with(device._effect_dict["colorful"][0])

    assert device.get_effect() == "colorful"


def test_effect_list_contains_lowercase_names():
    """Test that all effect names in get_effect_list are lowercase."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = bulb.SwitchbotBulb(ble_device)
    effect_list = device.get_effect_list

    assert effect_list is not None, "Effect list should not be None"
    assert effect_list == ["colorful", "flickering", "breathing"]
    for effect_name in effect_list:
        assert effect_name.islower(), f"Effect name '{effect_name}' is not lowercase"


@pytest.mark.asyncio
async def test_set_effect_normalizes_case():
    """Test that set_effect normalizes effect names to lowercase."""
    device = create_device_for_command_testing()

    # Test various case combinations
    test_cases = ["COLORFUL", "Colorful", "CoLoRfUl", "colorful"]

    for test_effect in test_cases:
        await device.set_effect(test_effect)
        # Should always work regardless of case
        device._send_command.assert_called()
        assert device.get_effect() == test_effect  # Stored as provided
