from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.const.fan import (
    FanMode,
    NightLightState,
    OscillationAngle,
    StandingFanMode,
)
from switchbot.devices import fan
from switchbot.devices.device import SwitchbotOperationError
from switchbot.devices.fan import SwitchbotStandingFan

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    init_data: dict | None = None, model: SwitchbotModel = SwitchbotModel.CIRCULATOR_FAN
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    fan_device = fan.SwitchbotFan(ble_device, model=model)
    fan_device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    fan_device._send_command = AsyncMock()
    fan_device._check_command_result = MagicMock()
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
    ("response", "expected"),
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
    ("basic_info", "firmware_info"), [(True, False), (False, True), (False, False)]
)
async def test_get_basic_info_returns_none(basic_info, firmware_info):
    fan_device = create_device_for_command_testing()

    async def mock_get_basic_info(arg):
        if arg == fan.COMMAND_GET_BASIC_INFO:
            return basic_info
        if arg == fan.DEVICE_GET_BASIC_SETTINGS_KEY:
            return firmware_info
        return None

    fan_device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    assert await fan_device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "firmware_info", "result"),
    [
        (
            bytearray(b"\x01\x02W\x82g\xf5\xde4\x01=dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01W\x0b\x17\x01"),
            [87, True, False, "normal", 61, 1.1],
        ),
        (
            bytearray(b"\x01\x02U\xc2g\xf5\xde4\x04+dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01U\x0b\x17\x01"),
            [85, True, True, "baby", 43, 1.1],
        ),
    ],
)
async def test_get_basic_info(basic_info, firmware_info, result):
    fan_device = create_device_for_command_testing()

    async def mock_get_basic_info(arg):
        if arg == fan.COMMAND_GET_BASIC_INFO:
            return basic_info
        if arg == fan.DEVICE_GET_BASIC_SETTINGS_KEY:
            return firmware_info
        return None

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
    fan_device = create_device_for_command_testing({"mode": "baby"})
    await fan_device.set_preset_mode("baby")
    assert fan_device.get_current_mode() == "baby"


@pytest.mark.asyncio
async def test_set_percentage_with_speed_is_0():
    fan_device = create_device_for_command_testing({"speed": 0, "isOn": False})
    await fan_device.turn_off()
    assert fan_device.get_current_percentage() == 0
    assert fan_device.is_on() is False


@pytest.mark.asyncio
async def test_set_percentage():
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
@pytest.mark.parametrize(
    ("oscillating", "expected_cmd"),
    [
        (True, fan.COMMAND_START_OSCILLATION),
        (False, fan.COMMAND_STOP_OSCILLATION),
    ],
)
async def test_circulator_fan_set_oscillation_command(oscillating, expected_cmd):
    """Circulator Fan keeps the original single-axis (V kept) payload."""
    fan_device = create_device_for_command_testing({"oscillating": oscillating})
    await fan_device.set_oscillation(oscillating)
    fan_device._send_command.assert_called_once()
    cmd = fan_device._send_command.call_args[0][0]
    assert cmd == expected_cmd


def test_circulator_fan_oscillation_command_constants():
    """Lock the bytes for the Circulator Fan oscillation commands."""
    # These are master-version bytes preserved for backward compatibility.
    assert fan.COMMAND_START_OSCILLATION == "570f41020101ff"
    assert fan.COMMAND_STOP_OSCILLATION == "570f41020102ff"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("oscillating", "expected_cmd"),
    [
        (True, fan.COMMAND_START_OSCILLATION_ALL_AXES),
        (False, fan.COMMAND_STOP_OSCILLATION_ALL_AXES),
    ],
)
async def test_standing_fan_set_oscillation_command(oscillating, expected_cmd):
    """Standing Fan oscillation toggles both axes at once."""
    standing_fan = create_standing_fan_for_testing({"oscillating": oscillating})
    await standing_fan.set_oscillation(oscillating)
    standing_fan._send_command.assert_called_once()
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == expected_cmd


def test_standing_fan_oscillation_command_constants():
    """Lock the bytes for the Standing Fan dual-axis oscillation commands."""
    assert fan.COMMAND_START_OSCILLATION_ALL_AXES == "570f4102010101"
    assert fan.COMMAND_STOP_OSCILLATION_ALL_AXES == "570f4102010202"


def _fan_with_real_result_check(init_data: dict | None = None):
    """
    Command-test fixture that uses the real _check_command_result.

    Unlike `create_device_for_command_testing`, this keeps the real
    `_check_command_result` so setter methods exercise the success-byte
    validation path.
    """
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    fan_device = fan.SwitchbotFan(ble_device, model=SwitchbotModel.CIRCULATOR_FAN)
    fan_device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    fan_device._send_command = AsyncMock()
    fan_device.update = AsyncMock()
    return fan_device


def _standing_fan_with_real_result_check(init_data: dict | None = None):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    standing_fan = SwitchbotStandingFan(ble_device, model=SwitchbotModel.STANDING_FAN)
    standing_fan.update_from_advertisement(
        make_advertisement_data(ble_device, init_data)
    )
    standing_fan._send_command = AsyncMock()
    standing_fan.update = AsyncMock()
    return standing_fan


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        # Success byte is 1.
        (b"\x01", True),
        (b"\x01\xff", True),
        # Known fan error payloads.
        (b"\x00", False),
        (b"\x07", False),
    ],
)
@pytest.mark.parametrize(
    "invoke",
    [
        lambda d: d.set_preset_mode("baby"),
        lambda d: d.set_percentage(80),
        lambda d: d.set_oscillation(True),
        lambda d: d.set_oscillation(False),
        lambda d: d.set_horizontal_oscillation(True),
        lambda d: d.set_vertical_oscillation(True),
    ],
)
async def test_circulator_fan_setters_validate_success_byte(response, expected, invoke):
    """Every Circulator Fan setter returns True only on success-byte 1."""
    device = _fan_with_real_result_check()
    device._send_command.return_value = response
    assert await invoke(device) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (b"\x01", True),
        (b"\x01\xff", True),
        (b"\x00", False),
        (b"\x07", False),
    ],
)
@pytest.mark.parametrize(
    "invoke",
    [
        lambda d: d.set_horizontal_oscillation_angle(OscillationAngle.ANGLE_60),
        lambda d: d.set_vertical_oscillation_angle(OscillationAngle.ANGLE_90),
        lambda d: d.set_night_light(NightLightState.LEVEL_1),
        lambda d: d.set_night_light(NightLightState.OFF),
    ],
)
async def test_standing_fan_setters_validate_success_byte(response, expected, invoke):
    """Every Standing Fan setter returns True only on success-byte 1."""
    device = _standing_fan_with_real_result_check()
    device._send_command.return_value = response
    assert await invoke(device) is expected


@pytest.mark.asyncio
async def test_fan_setter_raises_on_none_response():
    """None responses raise SwitchbotOperationError via _check_command_result."""
    device = _fan_with_real_result_check()
    device._send_command.return_value = None
    with pytest.raises(SwitchbotOperationError):
        await device.set_oscillation(True)


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
    assert FanMode.get_modes() == ["normal", "natural", "sleep", "baby"]


def create_standing_fan_for_testing(init_data: dict | None = None):
    """Create a SwitchbotStandingFan instance for command testing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    standing_fan = SwitchbotStandingFan(ble_device, model=SwitchbotModel.STANDING_FAN)
    standing_fan.update_from_advertisement(
        make_advertisement_data(ble_device, init_data)
    )
    standing_fan._send_command = AsyncMock()
    standing_fan._check_command_result = MagicMock()
    standing_fan.update = AsyncMock()
    return standing_fan


def test_standing_fan_inherits_from_switchbot_fan():
    assert issubclass(SwitchbotStandingFan, fan.SwitchbotFan)


def test_standing_fan_instantiation():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    standing_fan = SwitchbotStandingFan(ble_device, model=SwitchbotModel.STANDING_FAN)
    assert standing_fan is not None


def test_standing_fan_get_modes():
    assert StandingFanMode.get_modes() == [
        "normal",
        "natural",
        "sleep",
        "baby",
        "custom_natural",
    ]


@pytest.mark.asyncio
async def test_standing_fan_turn_on():
    standing_fan = create_standing_fan_for_testing({"isOn": True})
    await standing_fan.turn_on()
    assert standing_fan.is_on() is True


@pytest.mark.asyncio
async def test_standing_fan_turn_off():
    standing_fan = create_standing_fan_for_testing({"isOn": False})
    await standing_fan.turn_off()
    assert standing_fan.is_on() is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode",
    ["normal", "natural", "sleep", "baby", "custom_natural"],
)
async def test_standing_fan_set_preset_mode(mode):
    standing_fan = create_standing_fan_for_testing({"mode": mode})
    await standing_fan.set_preset_mode(mode)
    assert standing_fan.get_current_mode() == mode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "firmware_info", "result"),
    [
        (
            bytearray(b"\x01\x02W\x82g\xf5\xde4\x01=dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01W\x0b\x17\x01"),
            {
                "battery": 87,
                "isOn": True,
                "oscillating": False,
                "oscillating_horizontal": False,
                "oscillating_vertical": False,
                "mode": "normal",
                "speed": 61,
                "firmware": 1.1,
            },
        ),
        (
            bytearray(b"\x01\x02U\xc2g\xf5\xde4\x04+dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01U\x0b\x17\x01"),
            {
                "battery": 85,
                "isOn": True,
                "oscillating": True,
                "oscillating_horizontal": True,
                "oscillating_vertical": False,
                "mode": "baby",
                "speed": 43,
                "firmware": 1.1,
            },
        ),
        (
            bytearray(b"\x01\x02U\xe2g\xf5\xde4\x05+dPP\x03\x14P\x00\x00\x00\x00"),
            bytearray(b"\x01U\x0b\x17\x01"),
            {
                "battery": 85,
                "isOn": True,
                "oscillating": True,
                "oscillating_horizontal": True,
                "oscillating_vertical": True,
                "mode": "custom_natural",
                "speed": 43,
                "firmware": 1.1,
            },
        ),
    ],
)
async def test_standing_fan_get_basic_info(basic_info, firmware_info, result):
    # Preload nightLight via the fixture adv data so get_basic_info can surface it.
    standing_fan = create_standing_fan_for_testing({"nightLight": 3})

    async def mock_get_basic_info(arg):
        if arg == fan.COMMAND_GET_BASIC_INFO:
            return basic_info
        if arg == fan.DEVICE_GET_BASIC_SETTINGS_KEY:
            return firmware_info
        return None

    standing_fan._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    info = await standing_fan.get_basic_info()
    assert info == result | {"nightLight": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "firmware_info"),
    [(True, False), (False, True), (False, False)],
)
async def test_standing_fan_get_basic_info_returns_none(basic_info, firmware_info):
    standing_fan = create_standing_fan_for_testing()

    async def mock_get_basic_info(arg):
        if arg == fan.COMMAND_GET_BASIC_INFO:
            return basic_info
        if arg == fan.DEVICE_GET_BASIC_SETTINGS_KEY:
            return firmware_info
        return None

    standing_fan._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    assert await standing_fan.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "angle",
    [OscillationAngle.ANGLE_30, OscillationAngle.ANGLE_60, OscillationAngle.ANGLE_90],
)
async def test_standing_fan_set_horizontal_oscillation_angle(angle):
    standing_fan = create_standing_fan_for_testing()
    await standing_fan.set_horizontal_oscillation_angle(angle)
    standing_fan._send_command.assert_called_once()
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == f"{fan.COMMAND_SET_OSCILLATION_PARAMS}{angle.value:02X}FFFFFF"


@pytest.mark.asyncio
@pytest.mark.parametrize("angle", [30, 60, 90])
async def test_standing_fan_set_horizontal_oscillation_angle_int(angle):
    """Raw int inputs are coerced through OscillationAngle(angle)."""
    standing_fan = create_standing_fan_for_testing()
    await standing_fan.set_horizontal_oscillation_angle(angle)
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == f"{fan.COMMAND_SET_OSCILLATION_PARAMS}{angle:02X}FFFFFF"


@pytest.mark.asyncio
@pytest.mark.parametrize("angle", [0, 45, 120, -1])
async def test_standing_fan_set_horizontal_oscillation_angle_invalid(angle):
    standing_fan = create_standing_fan_for_testing()
    with pytest.raises(ValueError, match="is not a valid"):
        await standing_fan.set_horizontal_oscillation_angle(angle)
    standing_fan._send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "angle",
    [OscillationAngle.ANGLE_30, OscillationAngle.ANGLE_60, OscillationAngle.ANGLE_90],
)
async def test_standing_fan_set_vertical_oscillation_angle(angle):
    standing_fan = create_standing_fan_for_testing()
    await standing_fan.set_vertical_oscillation_angle(angle)
    standing_fan._send_command.assert_called_once()
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == f"{fan.COMMAND_SET_OSCILLATION_PARAMS}FFFF{angle.value:02X}FF"


@pytest.mark.asyncio
@pytest.mark.parametrize("angle", [0, 45, 120, -1])
async def test_standing_fan_set_vertical_oscillation_angle_invalid(angle):
    standing_fan = create_standing_fan_for_testing()
    with pytest.raises(ValueError, match="is not a valid"):
        await standing_fan.set_vertical_oscillation_angle(angle)
    standing_fan._send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [NightLightState.LEVEL_1, NightLightState.LEVEL_2, NightLightState.OFF],
)
async def test_standing_fan_set_night_light(state):
    standing_fan = create_standing_fan_for_testing()
    await standing_fan.set_night_light(state)
    standing_fan._send_command.assert_called_once()
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == f"{fan.COMMAND_SET_NIGHT_LIGHT}{state.value:02X}FFFF"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [1, 2, 3])
async def test_standing_fan_set_night_light_int(state):
    """Raw int inputs are coerced through NightLightState(state)."""
    standing_fan = create_standing_fan_for_testing()
    await standing_fan.set_night_light(state)
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == f"{fan.COMMAND_SET_NIGHT_LIGHT}{state:02X}FFFF"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [0, 4, 99, -1])
async def test_standing_fan_set_night_light_invalid(state):
    standing_fan = create_standing_fan_for_testing()
    with pytest.raises(ValueError, match="is not a valid"):
        await standing_fan.set_night_light(state)
    standing_fan._send_command.assert_not_called()


def test_standing_fan_get_night_light_state():
    standing_fan = create_standing_fan_for_testing({"nightLight": 1})
    assert standing_fan.get_night_light_state() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("oscillating", "expected_cmd"),
    [
        (True, fan.COMMAND_START_HORIZONTAL_OSCILLATION),
        (False, fan.COMMAND_STOP_HORIZONTAL_OSCILLATION),
    ],
)
async def test_standing_fan_set_horizontal_oscillation(oscillating, expected_cmd):
    standing_fan = create_standing_fan_for_testing({"oscillating": oscillating})
    await standing_fan.set_horizontal_oscillation(oscillating)
    standing_fan._send_command.assert_called_once()
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == expected_cmd


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("oscillating", "expected_cmd"),
    [
        (True, fan.COMMAND_START_VERTICAL_OSCILLATION),
        (False, fan.COMMAND_STOP_VERTICAL_OSCILLATION),
    ],
)
async def test_standing_fan_set_vertical_oscillation(oscillating, expected_cmd):
    standing_fan = create_standing_fan_for_testing({"oscillating": oscillating})
    await standing_fan.set_vertical_oscillation(oscillating)
    standing_fan._send_command.assert_called_once()
    cmd = standing_fan._send_command.call_args[0][0]
    assert cmd == expected_cmd


def test_standing_fan_get_horizontal_oscillating_state():
    standing_fan = create_standing_fan_for_testing({"oscillating_horizontal": True})
    assert standing_fan.get_horizontal_oscillating_state() is True


def test_standing_fan_get_vertical_oscillating_state():
    standing_fan = create_standing_fan_for_testing({"oscillating_vertical": True})
    assert standing_fan.get_vertical_oscillating_state() is True
