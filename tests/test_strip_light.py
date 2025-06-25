from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.const.light import ColorMode
from switchbot.devices import light_strip
from switchbot.devices.base_light import SwitchbotBaseLight
from switchbot.devices.device import SwitchbotEncryptedDevice, SwitchbotOperationError

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    init_data: dict | None = None, model: SwitchbotModel = SwitchbotModel.STRIP_LIGHT_3
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = light_strip.SwitchbotStripLight3(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=model
    )
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
            "rawAdvData": b"\x00\x00\x00\x00\x10\xd0\xb1",
            "data": {
                "sequence_number": 133,
                "isOn": True,
                "brightness": 30,
                "delay": False,
                "network_state": 2,
                "color_mode": 2,
                "cw": 4753,
            }
            | init_data,
            "isEncrypted": False,
            "model": b"\x00\x10\xd0\xb1",
            "modelFriendlyName": "Strip Light 3",
            "modelName": SwitchbotModel.STRIP_LIGHT_3,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_default_info():
    """Test default initialization of the strip light."""
    device = create_device_for_command_testing()

    assert device.rgb is None

    device._state = {"r": 30, "g": 0, "b": 0, "cw": 3200}

    assert device.is_on() is True
    assert device.on is True
    assert device.color_mode == ColorMode.RGB
    assert device.color_modes == {
        ColorMode.RGB,
        ColorMode.COLOR_TEMP,
    }
    assert device.rgb == (30, 0, 0)
    assert device.color_temp == 3200
    assert device.brightness == 30
    assert device.min_temp == 2700
    assert device.max_temp == 6500
    # Check that effect list contains expected lowercase effect names
    effect_list = device.get_effect_list
    assert effect_list is not None
    assert all(effect.islower() for effect in effect_list)
    # Verify some known effects are present
    assert "christmas" in effect_list
    assert "halloween" in effect_list
    assert "sunset" in effect_list


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
                "basic_info": b"\x01\x00<\xff\x00\xd8\x00\x19d\x00\x03",
                "version_info": b"\x01\x01\n",
            },
            [False, 60, 255, 0, 216, 6500, 3, 1.0],
        ),
        (
            {
                "basic_info": b"\x01\x80NK\xff:\x00\x19d\xff\x02",
                "version_info": b"\x01\x01\n",
            },
            [True, 78, 75, 255, 58, 6500, 2, 1.0],
        ),
        (
            {
                "basic_info": b"\x01\x80$K\xff:\x00\x13\xf9\xff\x06",
                "version_info": b"\x01\x01\n",
            },
            [True, 36, 75, 255, 58, 5113, 6, 1.0],
        ),
    ],
)
async def test_strip_light_get_basic_info(info_data, result):
    """Test getting basic info from the strip light."""
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
    """Test turning on the strip light."""
    device = create_device_for_command_testing({"isOn": True})

    await device.turn_on()

    device._send_command.assert_called_with(device._turn_on_command)

    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    """Test turning off the strip light."""
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
    device._send_multiple_commands = AsyncMock()

    await device.set_effect("christmas")

    device._send_multiple_commands.assert_called_with(device._effect_dict["christmas"])

    assert device.get_effect() == "christmas"


def test_effect_list_contains_lowercase_names():
    """Test that all effect names in get_effect_list are lowercase."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = light_strip.SwitchbotLightStrip(ble_device)
    effect_list = device.get_effect_list

    assert effect_list is not None, "Effect list should not be None"
    # All effect names should be lowercase
    for effect_name in effect_list:
        assert effect_name.islower(), f"Effect name '{effect_name}' is not lowercase"
    # Verify some known effects are present
    assert "christmas" in effect_list
    assert "halloween" in effect_list
    assert "sunset" in effect_list


@pytest.mark.asyncio
async def test_set_effect_normalizes_case():
    """Test that set_effect normalizes effect names to lowercase."""
    device = create_device_for_command_testing()
    device._send_multiple_commands = AsyncMock()

    # Test various case combinations
    test_cases = ["CHRISTMAS", "Christmas", "ChRiStMaS", "christmas"]

    for test_effect in test_cases:
        await device.set_effect(test_effect)
        # Should always work regardless of case
        device._send_multiple_commands.assert_called()
        assert device.get_effect() == test_effect  # Stored as provided


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await light_strip.SwitchbotStripLight3.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        SwitchbotModel.STRIP_LIGHT_3,
    )

    assert result is True


def create_strip_light_device(init_data: dict | None = None):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    return light_strip.SwitchbotLightStrip(ble_device)


@pytest.mark.asyncio
async def test_strip_light_supported_color_modes():
    """Test that the strip light supports the expected color modes."""
    device = create_strip_light_device()

    assert device.color_modes == {
        ColorMode.RGB,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("commands", "results", "final_result"),
    [
        (("command1", "command2"), [(b"\x01", False), (None, False)], False),
        (("command1", "command2"), [(None, False), (b"\x01", True)], True),
        (("command1", "command2"), [(b"\x01", True), (b"\x01", False)], True),
    ],
)
async def test_send_multiple_commands(commands, results, final_result):
    """Test sending multiple commands."""
    device = create_device_for_command_testing()

    device._send_command = AsyncMock(side_effect=[r[0] for r in results])

    device._check_command_result = MagicMock(side_effect=[r[1] for r in results])

    result = await device._send_multiple_commands(list(commands))

    assert result is final_result


@pytest.mark.asyncio
async def test_unimplemented_color_mode():
    class TestDevice(SwitchbotBaseLight):
        pass

    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = TestDevice(ble_device)

    with pytest.raises(NotImplementedError):
        _ = device.color_mode


@pytest.mark.asyncio
async def test_exception_with_wrong_model():
    class TestDevice(SwitchbotBaseLight):
        def __init__(self, device: BLEDevice, model: str = "unknown") -> None:
            super().__init__(device, model=model)

    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = TestDevice(ble_device)

    with pytest.raises(
        SwitchbotOperationError,
        match="Current device aa:bb:cc:dd:ee:ff does not support this functionality",
    ):
        await device.set_rgb(100, 255, 128, 64)
