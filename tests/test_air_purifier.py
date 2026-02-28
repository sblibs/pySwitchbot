from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotEncryptedDevice, SwitchbotModel
from switchbot.const.air_purifier import AirPurifierMode
from switchbot.devices import air_purifier

from .test_adv_parser import generate_ble_device

common_params = [
    (b"7\x00\x00\x95-\x00", "7", SwitchbotModel.AIR_PURIFIER_TABLE_US),
    (b"*\x00\x00\x15\x04\x00", "*", SwitchbotModel.AIR_PURIFIER_US),
    (b"+\x00\x00\x15\x04\x00", "+", SwitchbotModel.AIR_PURIFIER_JP),
    (b"8\x00\x00\x95-\x00", "8", SwitchbotModel.AIR_PURIFIER_TABLE_JP),
]


def create_device_for_command_testing(
    rawAdvData: bytes,
    model: str,
    model_name: SwitchbotModel,
    init_data: dict | None = None,
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = air_purifier.SwitchbotAirPurifier(
        ble_device,
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=model_name,
    )
    device.update = AsyncMock()
    device.update_from_advertisement(
        make_advertisement_data(ble_device, rawAdvData, model, model_name, init_data)
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice,
    rawAdvData: bytes,
    model: str,
    model_name: SwitchbotModel,
    init_data: dict | None = None,
):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": rawAdvData,
            "data": {
                "isOn": True,
                "mode": "level_3",
                "isAqiValid": False,
                "child_lock": False,
                "speed": 100,
                "aqi_level": "excellent",
                "filter element working time": 405,
                "err_code": 0,
                "sequence_number": 161,
            }
            | init_data,
            "isEncrypted": False,
            "model": model,
            "modelFriendlyName": "Air Purifier",
            "modelName": model_name,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "model_name"),
    common_params,
)
@pytest.mark.parametrize(
    "pm25",
    [150],
)
async def test_status_from_proceess_adv(rawAdvData, model, model_name, pm25):
    device = create_device_for_command_testing(
        rawAdvData, model, model_name, {"pm25": pm25}
    )
    assert device.get_current_percentage() == 100
    assert device.is_on() is True
    assert device.get_current_aqi_level() == "excellent"
    assert device.get_current_mode() == "level_3"
    assert device.get_current_pm25() == 150


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "model_name"),
    common_params,
)
async def test_get_basic_info_returns_none_when_no_data(rawAdvData, model, model_name):
    device = create_device_for_command_testing(rawAdvData, model, model_name)
    device._get_basic_info_by_multi_commands = AsyncMock(return_value=None)

    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "model_name"),
    common_params,
)
@pytest.mark.parametrize(
    "mode", ["level_1", "level_2", "level_3", "auto", "pet", "sleep"]
)
async def test_set_preset_mode(rawAdvData, model, model_name, mode):
    device = create_device_for_command_testing(
        rawAdvData, model, model_name, {"mode": mode}
    )
    await device.set_preset_mode(mode)
    assert device.get_current_mode() == mode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "model_name"),
    common_params,
)
async def test_turn_on(rawAdvData, model, model_name):
    device = create_device_for_command_testing(
        rawAdvData, model, model_name, {"isOn": True}
    )
    await device.turn_on()
    assert device.is_on() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "model_name"),
    common_params,
)
async def test_turn_off(rawAdvData, model, model_name):
    device = create_device_for_command_testing(
        rawAdvData, model, model_name, {"isOn": False}
    )
    await device.turn_off()
    assert device.is_on() is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "model_name"),
    common_params,
)
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (b"\x00", None),
        (b"\x07", None),
        (b"\x01\x02\x03", b"\x01\x02\x03"),
    ],
)
async def test__get_basic_info(rawAdvData, model, model_name, response, expected):
    device = create_device_for_command_testing(rawAdvData, model, model_name)
    device._send_command = AsyncMock(return_value=response)
    result = await device._get_basic_info()
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device_case",
    common_params,
)
@pytest.mark.parametrize(
    "info_case",
    [
        (
            bytearray(
                b"\x01\xa7\xe9\x8c\x08\x00\xb2\x01\x96\x00\x00\x00\xf0\x00\x00\x17"
            ),
            bytearray(b"\x01\x01\x11\x22\x33\x44"),
            bytearray(b"\x01\x03"),
            [
                True,
                2,
                "level_2",
                True,
                False,
                "excellent",
                50,
                0,
                2.3,
                0x44,
                True,
                True,
            ],
        ),
        (
            bytearray(
                b"\x01\xa8\xec\x8c\x08\x00\xb2\x01\x96\x00\x00\x00\xf0\x00\x00\x17"
            ),
            bytearray(b"\x01\x01\xaa\xbb\xcc\x1e"),
            bytearray(b"\x01\x00"),
            [
                True,
                2,
                "pet",
                True,
                False,
                "excellent",
                50,
                0,
                2.3,
                0x1E,
                False,
                False,
            ],
        ),
    ],
)
async def test_get_basic_info(device_case, info_case):
    rawAdvData, model, model_name = device_case
    basic_info, led_settings, led_status, result = info_case
    device = create_device_for_command_testing(rawAdvData, model, model_name)
    device._get_basic_info_by_multi_commands = AsyncMock(
        return_value=[basic_info, led_settings, led_status]
    )

    info = await device.get_basic_info()
    assert info["isOn"] == result[0]
    assert info["version_info"] == result[1]
    assert info["mode"] == result[2]
    assert info["isAqiValid"] == result[3]
    assert info["child_lock"] == result[4]
    assert info["aqi_level"] == result[5]
    assert info["speed"] == result[6]
    if model_name not in (
        SwitchbotModel.AIR_PURIFIER_JP,
        SwitchbotModel.AIR_PURIFIER_TABLE_JP,
    ):
        assert info["pm25"] == result[7]
    else:
        assert "pm25" not in info
    assert info["firmware"] == result[8]
    assert info["brightness"] == result[9]
    assert info["light_sensitive"] == result[10]
    assert info["led_status"] == result[11]


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await air_purifier.SwitchbotAirPurifier.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        SwitchbotModel.AIR_PURIFIER_US,
    )

    assert result is True


def test_get_modes():
    assert AirPurifierMode.get_modes() == [
        "level_1",
        "level_2",
        "level_3",
        "auto",
        "sleep",
        "pet",
    ]


@pytest.mark.asyncio
async def test_air_purifier_color_and_led_properties():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(
        raw_adv,
        model,
        model_name,
        {"led_status": True},
    )

    assert device.color_modes == {air_purifier.ColorMode.RGB}
    assert device.color_mode == air_purifier.ColorMode.RGB
    assert device.is_led_on is True


@pytest.mark.asyncio
async def test_read_led_settings():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(raw_adv, model, model_name)

    device._send_command = AsyncMock(return_value=None)
    assert await device.read_led_settings() is None

    device._send_command = AsyncMock(return_value=b"\x01\x00\x0d")
    assert await device.read_led_settings() == {"led_brightness": 3, "led_color": 1}


@pytest.mark.asyncio
async def test_set_percentage_validation_and_command():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(
        raw_adv,
        model,
        model_name,
        {"mode": "level_2"},
    )
    device._check_command_result = MagicMock(return_value=True)
    device._send_command = AsyncMock(return_value=b"\x01")

    assert await device.set_percentage(25) is True
    device._send_command.assert_called_with(
        air_purifier.COMMAND_SET_PERCENTAGE.format(percentage=25)
    )

    with pytest.raises(AssertionError, match="Percentage must be between 0 and 100"):
        await device.set_percentage(-1)
    with pytest.raises(AssertionError, match="Percentage must be between 0 and 100"):
        await device.set_percentage(101)

    invalid_mode_device = create_device_for_command_testing(
        raw_adv,
        model,
        model_name,
        {"mode": "auto"},
    )
    with pytest.raises(ValueError, match="Percentage can only be set in LEVEL modes"):
        await invalid_mode_device.set_percentage(10)


@pytest.mark.asyncio
async def test_set_brightness_validation_and_command():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(raw_adv, model, model_name)
    device._state = {"r": 1, "g": 2, "b": 3}
    device._check_command_result = MagicMock(return_value=True)
    device._send_command = AsyncMock(return_value=b"\x01")

    assert await device.set_brightness(10) is True
    device._send_command.assert_called_with(
        device._set_brightness_command.format("0102030A")
    )

    with pytest.raises(AssertionError, match="Brightness must be between 0 and 100"):
        await device.set_brightness(101)


@pytest.mark.asyncio
async def test_set_rgb_validation_and_command():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(raw_adv, model, model_name)
    device._check_command_result = MagicMock(return_value=True)
    device._send_command = AsyncMock(return_value=b"\x01")

    assert await device.set_rgb(20, 1, 2, 3) is True
    device._send_command.assert_called_with(device._set_rgb_command.format("01020314"))

    with pytest.raises(AssertionError, match="Brightness must be between 0 and 100"):
        await device.set_rgb(101, 1, 2, 3)
    with pytest.raises(AssertionError, match="r must be between 0 and 255"):
        await device.set_rgb(10, 256, 2, 3)
    with pytest.raises(AssertionError, match="g must be between 0 and 255"):
        await device.set_rgb(10, 1, 256, 3)
    with pytest.raises(AssertionError, match="b must be between 0 and 255"):
        await device.set_rgb(10, 1, 2, 256)


@pytest.mark.asyncio
async def test_led_and_light_sensitive_commands():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(
        raw_adv, model, model_name, {"led_status": True}
    )
    device._check_command_result = MagicMock(return_value=True)
    device._send_command = AsyncMock(return_value=b"\x01")

    assert await device.turn_led_on() is True
    device._send_command.assert_called_with(device._turn_led_on_command)

    assert await device.turn_led_off() is True
    device._send_command.assert_called_with(device._turn_led_off_command)

    assert await device.open_light_sensitive() is True
    device._send_command.assert_called_with(device._open_light_sensitive_command)

    assert await device.close_light_sensitive() is True
    device._send_command.assert_called_with(device._turn_led_on_command)

    device_off = create_device_for_command_testing(
        raw_adv,
        model,
        model_name,
        {"led_status": False},
    )
    device_off._check_command_result = MagicMock(return_value=True)
    device_off._send_command = AsyncMock(return_value=b"\x01")
    assert await device_off.close_light_sensitive() is True
    device_off._send_command.assert_called_with(device_off._turn_led_off_command)


@pytest.mark.asyncio
async def test_air_purifier_cache_getters():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(
        raw_adv,
        model,
        model_name,
        {
            "child_lock": True,
            "wireless_charging": True,
            "light_sensitive": True,
            "speed": 88,
        },
    )

    assert device.get_current_percentage() == 88
    assert device.is_child_lock_on() is True
    assert device.is_wireless_charging_on() is True
    assert device.is_light_sensitive_on() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation_case",
    [
        ("open_child_lock", "_open_child_lock_command"),
        ("close_child_lock", "_close_child_lock_command"),
        ("open_wireless_charging", "_open_wireless_charging_command"),
        ("close_wireless_charging", "_close_wireless_charging_command"),
    ],
)
async def test_child_lock_and_wireless_charging_operations(operation_case):
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(raw_adv, model, model_name)
    operation_name, command_attr = operation_case
    command = getattr(device, command_attr)

    device._check_function_support = MagicMock()
    device._check_command_result = MagicMock(return_value=True)
    device._send_command = AsyncMock(return_value=b"\x01")

    operation = getattr(device, operation_name)
    assert await operation() is True

    device._check_function_support.assert_called_with(command)
    device._send_command.assert_called_with(command)
    device._check_command_result.assert_called_with(b"\x01", 0, {1})
