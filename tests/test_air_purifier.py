from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio
from bleak.backends.device import BLEDevice

from switchbot import (
    SwitchBotAdvertisement,
    SwitchbotModel,
    SwitchbotOperationError,
)
from switchbot.const.air_purifier import AirPurifierMode
from switchbot.devices import air_purifier

from .test_adv_parser import generate_ble_device

common_params = [
    (b"7\x00\x00\x95-\x00", "7", SwitchbotModel.AIR_PURIFIER_TABLE_US),
    (b"*\x00\x00\x15\x04\x00", "*", SwitchbotModel.AIR_PURIFIER_US),
    (b"+\x00\x00\x15\x04\x00", "+", SwitchbotModel.AIR_PURIFIER_JP),
    (b"8\x00\x00\x95-\x00", "8", SwitchbotModel.AIR_PURIFIER_TABLE_JP),
]


@pytest_asyncio.fixture(params=common_params, ids=["table_us", "us", "jp", "table_jp"])
async def filter_reset_device(
    request: pytest.FixtureRequest,
) -> air_purifier.SwitchbotAirPurifier:
    raw_adv, model, model_name = request.param
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = air_purifier.SwitchbotAirPurifier(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=model_name
    )
    device.update = AsyncMock()
    device.update_from_advertisement(
        make_advertisement_data(ble_device, raw_adv, model, model_name)
    )
    return device


@pytest.mark.asyncio
async def test_reset_filter_usage(
    filter_reset_device: air_purifier.SwitchbotAirPurifier,
) -> None:
    device = filter_reset_device
    initial_data = device.parsed_data.copy()
    listener = MagicMock()
    unsubscribe = device.subscribe(listener)
    with patch.object(
        device, "_send_command", AsyncMock(side_effect=[b"\x01", b"\x01\x00\x00"])
    ) as send_command:
        assert await device.reset_filter_usage() is True
        assert send_command.await_args_list == [
            call("570f4c09", retry=0),
            call("570f4d09"),
        ]
    assert device.parsed_data == initial_data | {"filter element working time": 0}
    listener.assert_called_once_with()
    unsubscribe()

    advertisement = device._sb_adv_data
    assert advertisement is not None
    device.update_from_advertisement(
        make_advertisement_data(
            advertisement.device,
            advertisement.data["rawAdvData"],
            advertisement.data["model"],
            advertisement.data["modelName"],
            {"filter element working time": 1},
        )
    )
    assert device.parsed_data["filter element working time"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reset_response", "read_response", "message", "expected_calls"),
    [
        pytest.param(None, None, "Sending command failed", 1, id="no_reset_reply"),
        pytest.param(b"", None, "Sending command failed", 1, id="empty_reset_reply"),
        pytest.param(b"\x02", None, "reset was rejected", 1, id="reset_rejected"),
        pytest.param(b"\x01", None, "could not be verified", 2, id="no_read_reply"),
        pytest.param(b"\x01", b"", "could not be verified", 2, id="empty_read_reply"),
        pytest.param(
            b"\x01", b"\x01", "could not be verified", 2, id="short_read_reply"
        ),
        pytest.param(
            b"\x01", b"\x01\x00", "could not be verified", 2, id="partial_counter"
        ),
        pytest.param(
            b"\x01", b"\x02\x00\x00", "read was rejected", 2, id="read_rejected"
        ),
        pytest.param(
            b"\x01", b"\x01\x07\x68", "1896 used hours", 2, id="counter_not_reset"
        ),
    ],
)
async def test_reset_filter_usage_failure(
    filter_reset_device: air_purifier.SwitchbotAirPurifier,
    reset_response: bytes | None,
    read_response: bytes | None,
    message: str,
    expected_calls: int,
) -> None:
    device = filter_reset_device
    initial_data = device.parsed_data.copy()
    listener = MagicMock()
    device.subscribe(listener)
    with patch.object(
        device, "_send_command", AsyncMock(side_effect=[reset_response, read_response])
    ) as send_command:
        with pytest.raises(SwitchbotOperationError, match=message):
            await device.reset_filter_usage()
        assert send_command.await_count == expected_calls
    assert device.parsed_data == initial_data
    listener.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("responses", "expected_calls"),
    [
        pytest.param(
            [SwitchbotOperationError("Connection failed")], 1, id="reset_connection"
        ),
        pytest.param(
            [b"\x01", SwitchbotOperationError("Connection failed")],
            2,
            id="read_connection",
        ),
    ],
)
async def test_reset_filter_usage_transport_failure(
    filter_reset_device: air_purifier.SwitchbotAirPurifier,
    responses: list[bytes | SwitchbotOperationError],
    expected_calls: int,
) -> None:
    device = filter_reset_device
    initial_data = device.parsed_data.copy()
    listener = MagicMock()
    device.subscribe(listener)
    with patch.object(
        device, "_send_command", AsyncMock(side_effect=responses)
    ) as send_command:
        with pytest.raises(SwitchbotOperationError, match="Connection failed"):
            await device.reset_filter_usage()
        assert send_command.await_count == expected_calls
    assert device.parsed_data == initial_data
    listener.assert_not_called()


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
async def test_status_from_process_adv(rawAdvData, model, model_name, pm25):
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
                b"\x01\xa7\xe9\x8c\x08\x00\xb2\x01\x96\x00\x00\x00\x00\x01\x00\x17"
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
                1,
                2.3,
                0x44,
                True,
            ],
        ),
        (
            bytearray(
                b"\x01\xa8\xec\x8c\x08\x00\xb2\x01\x96\x00\x00\x00\x01\x00\x00\x17"
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
                256,
                2.3,
                0x1E,
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


GOOD_POLL_REPLIES = [
    bytes.fromhex("012fd20e0a008000200000000010001e"),
    bytes.fromhex("010000000064"),
    bytes.fromhex("0100"),
]
# A duplicated notification (here the encryption init reply) answered the basic
# info command, shifting each real reply one command later (US, firmware 3.0).
SHIFTED_POLL_REPLIES = [
    bytes.fromhex("01459d6b2268da72aa245d92cf562f0be8"),
    bytes.fromhex("0130d20e0a00800020000000000f001e"),
    bytes.fromhex("010000000064"),
]


@pytest.mark.asyncio
async def test_get_basic_info_firmware_3_0():
    device = create_device_for_command_testing(*common_params[1])
    device._send_command = AsyncMock(side_effect=GOOD_POLL_REPLIES)
    del device._check_command_result

    info = await device.get_basic_info()

    assert info["mode"] == "auto"
    assert info["isAqiValid"] is True
    assert info["child_lock"] is True
    assert info["speed"] == 0
    assert info["pm25"] == 16
    assert info["firmware"] == 3.0
    assert info["brightness"] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "replies",
    [
        pytest.param(SHIFTED_POLL_REPLIES, id="shifted_replies"),
        pytest.param(
            [
                bytes.fromhex("0102"),
                bytes.fromhex("01a4d20a09008000210000000007001e"),
                bytes.fromhex("01a6d20a09008000210000000007001e"),
            ],
            id="duplicated_command_reply",
        ),
        pytest.param(
            [GOOD_POLL_REPLIES[0], b"\x01\x00", GOOD_POLL_REPLIES[2]],
            id="short_led_settings",
        ),
        pytest.param(
            [GOOD_POLL_REPLIES[0], GOOD_POLL_REPLIES[1], b"\x01"],
            id="short_led_status",
        ),
    ],
)
async def test_update_ignores_mismatched_replies(replies):
    device = create_device_for_command_testing(*common_params[1], {"pm25": 16})
    device._send_command = AsyncMock(side_effect=replies)
    del device._check_command_result
    del device.update

    await device.update()

    assert device.get_current_pm25() == 16
    assert device.get_current_percentage() == 100
    assert "r" not in device._state


def test_default_model_classvar():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = air_purifier.SwitchbotAirPurifier(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff"
    )
    assert device._model == SwitchbotModel.AIR_PURIFIER_US


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
    )

    assert device.color_modes == {air_purifier.ColorMode.RGB}
    assert device.color_mode == air_purifier.ColorMode.RGB


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

    with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
        await device.set_percentage(-1)
    with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
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

    with pytest.raises(ValueError, match="Brightness must be between 0 and 100"):
        await device.set_brightness(101)


@pytest.mark.asyncio
async def test_set_rgb_validation_and_command():
    raw_adv, model, model_name = common_params[0]
    device = create_device_for_command_testing(raw_adv, model, model_name)
    device._check_command_result = MagicMock(return_value=True)
    device._send_command = AsyncMock(return_value=b"\x01")

    assert await device.set_rgb(20, 1, 2, 3) is True
    device._send_command.assert_called_with(device._set_rgb_command.format("01020314"))

    with pytest.raises(ValueError, match="Brightness must be between 0 and 100"):
        await device.set_rgb(101, 1, 2, 3)
    with pytest.raises(ValueError, match="r must be between 0 and 255"):
        await device.set_rgb(10, 256, 2, 3)
    with pytest.raises(ValueError, match="g must be between 0 and 255"):
        await device.set_rgb(10, 1, 256, 3)
    with pytest.raises(ValueError, match="b must be between 0 and 255"):
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

    assert await device.open_light_sensitive_switch() is True
    device._send_command.assert_called_with(device._open_light_sensitive_switch_command)

    assert await device.close_light_sensitive_switch() is True
    device._send_command.assert_called_with(device._turn_led_on_command)

    device_off = create_device_for_command_testing(
        raw_adv,
        model,
        model_name,
    )
    device_off._check_command_result = MagicMock(return_value=True)
    device_off._send_command = AsyncMock(return_value=b"\x01")
    assert await device_off.close_light_sensitive_switch() is True
    device_off._send_command.assert_called_with(device_off._turn_led_on_command)


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
    ],
)
async def test_child_lock_operations(operation_case):
    """Child lock commands should always be forwarded correctly."""
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_adv", "model", "model_name", "supported"),
    [
        (*common_params[0], True),
        (*common_params[3], True),
        (*common_params[1], False),
        (*common_params[2], False),
    ],
)
async def test_wireless_charging_model_support(raw_adv, model, model_name, supported):
    """Wireless charging operations should only succeed for table variants."""
    device = create_device_for_command_testing(raw_adv, model, model_name)
    if supported:
        device._check_command_result = MagicMock(return_value=True)
        device._send_command = AsyncMock(return_value=b"\x01")

        assert await device.open_wireless_charging() is True
        assert await device.close_wireless_charging() is True

        assert device._send_command.call_args_list == [
            ((device._open_wireless_charging_command,),),
            ((device._close_wireless_charging_command,),),
        ]

    else:
        with pytest.raises(SwitchbotOperationError):
            await device.open_wireless_charging()
        with pytest.raises(SwitchbotOperationError):
            await device.close_wireless_charging()
