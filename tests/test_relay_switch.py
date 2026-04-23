from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.adv_parsers.relay_switch import process_relay_switch_2pm
from switchbot.devices import relay_switch
from switchbot.devices.device import _merge_data as merge_data

from .test_adv_parser import generate_ble_device

common_params = [
    (b";\x00\x00\x00", SwitchbotModel.RELAY_SWITCH_1),
    (b"<\x00\x00\x00", SwitchbotModel.RELAY_SWITCH_1PM),
    (b">\x00\x00\x00", SwitchbotModel.GARAGE_DOOR_OPENER),
    (b"?\x00\x00\x00", SwitchbotModel.PLUG_MINI_EU),
]


@pytest.fixture
def common_parametrize_2pm():
    """Provide common test data."""
    return {
        "rawAdvData": b"\x00\x00\x00\x00\x00\x00",
        "model": SwitchbotModel.RELAY_SWITCH_2PM,
    }


def create_device_for_command_testing(
    rawAdvData: bytes, model: str, init_data: dict | None = None
):
    """Create a device for command testing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    if model == SwitchbotModel.GARAGE_DOOR_OPENER:
        device_class = relay_switch.SwitchbotGarageDoorOpener
    elif model == SwitchbotModel.RELAY_SWITCH_2PM:
        device_class = relay_switch.SwitchbotRelaySwitch2PM
    else:
        device_class = relay_switch.SwitchbotRelaySwitch
    device = device_class(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=model
    )
    device.update_from_advertisement(
        make_advertisement_data(ble_device, rawAdvData, model, init_data)
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice, rawAdvData: bytes, model: str, init_data: dict | None = None
):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}
    if model == SwitchbotModel.RELAY_SWITCH_2PM:
        return SwitchBotAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            data={
                "rawAdvData": rawAdvData,
                "data": {
                    1: {
                        "switchMode": True,
                        "sequence_number": 99,
                        "isOn": True,
                    },
                    2: {
                        "switchMode": True,
                        "sequence_number": 99,
                        "isOn": False,
                    },
                }
                | init_data,
                "isEncrypted": False,
            },
            device=ble_device,
            rssi=-80,
            active=True,
        )
    if model == SwitchbotModel.GARAGE_DOOR_OPENER:
        return SwitchBotAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            data={
                "rawAdvData": rawAdvData,
                "data": {
                    "switchMode": True,
                    "sequence_number": 96,
                    "isOn": True,
                    "door_open": False,
                }
                | init_data,
                "isEncrypted": False,
            },
            device=ble_device,
            rssi=-80,
            active=True,
        )
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": rawAdvData,
            "data": {
                "switchMode": True,
                "sequence_number": 96,
                "isOn": True,
            }
            | init_data,
            "isEncrypted": False,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "init_data",
    [
        {1: {"isOn": True}, 2: {"isOn": True}},
    ],
)
async def test_turn_on_2PM(common_parametrize_2pm, init_data) -> None:
    """Test turn on command."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"], init_data
    )
    await device.turn_on(1)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_ON[common_parametrize_2pm["model"]][1]
    )
    assert device.is_on(1) is True

    await device.turn_on(2)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_ON[common_parametrize_2pm["model"]][2]
    )
    assert device.is_on(2) is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "init_data",
    [
        {1: {"isOn": False}, 2: {"isOn": False}},
    ],
)
async def test_turn_off_2PM(common_parametrize_2pm, init_data) -> None:
    """Test turn off command."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"], init_data
    )
    await device.turn_off(1)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_OFF[common_parametrize_2pm["model"]][1]
    )
    assert device.is_on(1) is False

    await device.turn_off(2)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TURN_OFF[common_parametrize_2pm["model"]][2]
    )
    assert device.is_on(2) is False


@pytest.mark.asyncio
async def test_turn_toggle_2PM(common_parametrize_2pm) -> None:
    """Test toggle command."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"]
    )
    await device.async_toggle(1)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TOGGLE[common_parametrize_2pm["model"]][1]
    )
    assert device.is_on(1) is True

    await device.async_toggle(2)
    device._send_command.assert_called_with(
        relay_switch.MULTI_CHANNEL_COMMANDS_TOGGLE[common_parametrize_2pm["model"]][2]
    )
    assert device.is_on(2) is False


@pytest.mark.asyncio
async def test_get_switch_mode_2PM(common_parametrize_2pm) -> None:
    """Test get switch mode."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"]
    )
    assert device.switch_mode(1) is True
    assert device.switch_mode(2) is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("info_data", "result"),
    [
        (
            {
                "basic_info": b"\x01\x98A\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10",
                "channel1_info": b"\x01\x00\x00\x00\x00\x00\x00\x02\x99\x00\xe9\x00\x03\x00\x00",
                "channel2_info": b"\x01\x00\x055\x00'<\x02\x9f\x00\xe9\x01,\x00F",
            },
            [False, 0, 0, 0, 0, True, 0.02, 23, 0.3, 7.0],
        ),
        (
            {
                "basic_info": b"\x01\x9e\x81\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10",
                "channel1_info": b"\x01\x00\x00\x00\x00\x00\x00\x02\x99\x00\xe9\x00\x03\x00\x00",
                "channel2_info": b"\x01\x00\x05\xbc\x00'<\x02\xb1\x00\xea\x01-\x00F",
            },
            [True, 0, 23, 0.1, 0.0, False, 0.02, 0, 0, 0],
        ),
    ],
)
async def test_get_basic_info_2PM(common_parametrize_2pm, info_data, result) -> None:
    """Test get_basic_info for 2PM devices."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"]
    )

    assert device.channel == 2

    device.get_current_time_and_start_time = MagicMock(
        return_value=("683074d6", "682fba80")
    )

    async def mock_get_basic_info(arg):
        if arg == relay_switch.COMMAND_GET_BASIC_INFO:
            return info_data["basic_info"]
        if arg == relay_switch.COMMAND_GET_CHANNEL1_INFO.format("683074d6", "682fba80"):
            return info_data["channel1_info"]
        if arg == relay_switch.COMMAND_GET_CHANNEL2_INFO.format("683074d6", "682fba80"):
            return info_data["channel2_info"]
        return None

    device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    info = await device.get_basic_info()

    assert info is not None
    assert 1 in info
    assert 2 in info

    assert info[1]["isOn"] == result[0]
    assert info[1]["energy"] == result[1]
    assert info[1]["voltage"] == result[2]
    assert info[1]["current"] == result[3]
    assert info[1]["power"] == result[4]

    assert info[2]["isOn"] == result[5]
    assert info[2]["energy"] == result[6]
    assert info[2]["voltage"] == result[7]
    assert info[2]["current"] == result[8]
    assert info[2]["power"] == result[9]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "info_data",
    [
        {
            "basic_info": None,
            "channel1_info": b"\x01\x00\x00\x00\x00\x00\x00\x02\x99\x00\xe9\x00\x03\x00\x00",
            "channel2_info": b"\x01\x00\x055\x00'<\x02\x9f\x00\xe9\x01,\x00F",
        },
        {
            "basic_info": b"\x01\x98A\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10",
            "channel1_info": None,
            "channel2_info": b"\x01\x00\x055\x00'<\x02\x9f\x00\xe9\x01,\x00F",
        },
        {
            "basic_info": b"\x01\x98A\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10",
            "channel1_info": b"\x01\x00\x00\x00\x00\x00\x00\x02\x99\x00\xe9\x00\x03\x00\x00",
            "channel2_info": None,
        },
    ],
)
async def test_basic_info_exceptions_2PM(common_parametrize_2pm, info_data) -> None:
    """Test get_basic_info exceptions."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"]
    )

    device.get_current_time_and_start_time = MagicMock(
        return_value=("683074d6", "682fba80")
    )

    async def mock_get_basic_info(arg):
        if arg == relay_switch.COMMAND_GET_BASIC_INFO:
            return info_data["basic_info"]
        if arg == relay_switch.COMMAND_GET_CHANNEL1_INFO.format("683074d6", "682fba80"):
            return info_data["channel1_info"]
        if arg == relay_switch.COMMAND_GET_CHANNEL2_INFO.format("683074d6", "682fba80"):
            return info_data["channel2_info"]
        return None

    device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    info = await device.get_basic_info()

    assert info is None


@pytest.mark.asyncio
async def test_get_parsed_data_2PM(common_parametrize_2pm) -> None:
    """Test get_parsed_data for 2PM devices."""
    device = create_device_for_command_testing(
        common_parametrize_2pm["rawAdvData"], common_parametrize_2pm["model"]
    )

    info = device.get_parsed_data(1)
    assert info["isOn"] is True

    info = device.get_parsed_data(2)
    assert info["isOn"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
async def test_turn_on(rawAdvData, model) -> None:
    """Test turn on command."""
    device = create_device_for_command_testing(rawAdvData, model)
    await device.turn_on()
    device._send_command.assert_awaited_once_with(device._turn_on_command)
    assert device.is_on() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
async def test_turn_off(rawAdvData, model) -> None:
    """Test turn off command."""
    device = create_device_for_command_testing(rawAdvData, model, {"isOn": False})
    await device.turn_off()
    device._send_command.assert_awaited_once_with(device._turn_off_command)
    assert device.is_on() is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
async def test_toggle(rawAdvData, model) -> None:
    """Test toggle command."""
    device = create_device_for_command_testing(rawAdvData, model)
    await device.async_toggle()
    device._send_command.assert_awaited_once_with(relay_switch.COMMAND_TOGGLE)
    assert device.is_on() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model", "info_data"),
    [
        (
            b">\x00\x00\x00",
            SwitchbotModel.GARAGE_DOOR_OPENER,
            {
                "basic_info": b"\x01>\x80\x0c\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x10",
                "channel1_info": b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            },
        )
    ],
)
async def test_get_basic_info_garage_door_opener(rawAdvData, model, info_data) -> None:
    """Test get_basic_info for garage door opener."""
    device = create_device_for_command_testing(rawAdvData, model)
    device.get_current_time_and_start_time = MagicMock(
        return_value=("683074d6", "682fba80")
    )

    async def mock_get_basic_info(arg):
        if arg == relay_switch.COMMAND_GET_BASIC_INFO:
            return info_data["basic_info"]
        if arg == relay_switch.COMMAND_GET_CHANNEL1_INFO.format("683074d6", "682fba80"):
            return info_data["channel1_info"]
        return None

    device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)
    info = await device.get_basic_info()
    assert info is not None
    assert info["isOn"] is True
    assert info["door_open"] is True


@pytest.mark.parametrize(
    ("dev_cls", "expected_model"),
    [
        (relay_switch.SwitchbotRelaySwitch, SwitchbotModel.RELAY_SWITCH_1PM),
        (relay_switch.SwitchbotGarageDoorOpener, SwitchbotModel.GARAGE_DOOR_OPENER),
        (relay_switch.SwitchbotRelaySwitch2PM, SwitchbotModel.RELAY_SWITCH_2PM),
    ],
)
def test_default_model_classvar(dev_cls, expected_model) -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = dev_cls(ble_device, "ff", "ffffffffffffffffffffffffffffffff")
    assert device._model == expected_model


@pytest.mark.parametrize(
    ("old_data", "new_data", "expected_result"),
    [
        (
            {"isOn": True, "sequence_number": 1},
            {"isOn": False},
            {"isOn": False, "sequence_number": 1},
        ),
        (
            {
                1: {"current": 0, "voltage": 220, "power": 0},
                2: {"current": 1, "voltage": 0, "power": 10},
            },
            {1: {"current": 1, "power": 10}, 2: {"current": 0, "voltage": 220}},
            {
                1: {"current": 1, "voltage": 220, "power": 10},
                2: {"current": 0, "voltage": 220, "power": 10},
            },
        ),
    ],
)
def test_merge_data(old_data, new_data, expected_result) -> None:
    """Test merging of data dictionaries."""
    result = merge_data(old_data, new_data)
    assert result == expected_result


@pytest.mark.asyncio
async def test_garage_door_opener_open() -> None:
    """Test open the garage door."""
    device = create_device_for_command_testing(
        b">\x00\x00\x00", SwitchbotModel.GARAGE_DOOR_OPENER
    )

    await device.open()
    device._send_command.assert_awaited_once_with(device._open_command)


@pytest.mark.asyncio
async def test_garage_door_opener_close() -> None:
    """Test close the garage door."""
    device = create_device_for_command_testing(
        b">\x00\x00\x00", SwitchbotModel.GARAGE_DOOR_OPENER
    )

    await device.close()
    device._send_command.assert_awaited_once_with(device._close_command)


@pytest.mark.parametrize(
    "door_open",
    [
        True,
        False,
    ],
)
@pytest.mark.asyncio
async def test_garage_door_opener_door_open(door_open) -> None:
    """Test get garage door state."""
    device = create_device_for_command_testing(
        b">\x00\x00\x00", SwitchbotModel.GARAGE_DOOR_OPENER, {"door_open": door_open}
    )
    assert device.door_open() is door_open


@pytest.mark.asyncio
async def test_press() -> None:
    """Test the press command for garage door opener."""
    device = create_device_for_command_testing(
        b">\x00\x00\x00", SwitchbotModel.GARAGE_DOOR_OPENER
    )
    await device.press()
    device._send_command.assert_awaited_once_with(device._press_command)


def create_2pm_device_with_position(position: int = 50, calibration: bool = True):
    """Create a 2PM device with position/calibration data for cover testing."""
    return create_device_for_command_testing(
        b"\x00\x00\x00\x00\x00\x00",
        SwitchbotModel.RELAY_SWITCH_2PM,
        {
            1: {
                "switchMode": True,
                "sequence_number": 99,
                "isOn": True,
                "position": position,
                "calibration": calibration,
                "mode": 0,
            },
            2: {
                "switchMode": True,
                "sequence_number": 99,
                "isOn": False,
                "position": position,
                "calibration": calibration,
                "mode": 0,
            },
        },
    )


@pytest.mark.asyncio
async def test_2pm_open() -> None:
    """Test open command for 2PM roller mode."""
    device = create_2pm_device_with_position()
    await device.open()
    device._send_command.assert_called_with(relay_switch.COMMAND_OPEN)
    assert device.is_opening() is True
    assert device.is_closing() is False


@pytest.mark.asyncio
async def test_2pm_close() -> None:
    """Test close command for 2PM roller mode."""
    device = create_2pm_device_with_position()
    await device.close()
    device._send_command.assert_called_with(relay_switch.COMMAND_CLOSE)
    assert device.is_opening() is False
    assert device.is_closing() is True


@pytest.mark.asyncio
async def test_2pm_stop() -> None:
    """Test stop command for 2PM roller mode."""
    device = create_2pm_device_with_position()
    await device.stop()
    device._send_command.assert_called_with(relay_switch.COMMAND_STOP)
    assert device.is_opening() is False
    assert device.is_closing() is False


@pytest.mark.asyncio
async def test_2pm_set_position_closing() -> None:
    """Test set_position to a higher device position (closing in HA terms)."""
    device = create_2pm_device_with_position(position=30)
    await device.set_position(80)
    device._send_command.assert_called_with(
        relay_switch.COMMAND_POSITION.format(f"{80:02X}")
    )
    assert device.is_opening() is False
    assert device.is_closing() is True


@pytest.mark.asyncio
async def test_2pm_set_position_opening() -> None:
    """Test set_position to a lower device position (opening in HA terms)."""
    device = create_2pm_device_with_position(position=80)
    await device.set_position(20)
    device._send_command.assert_called_with(
        relay_switch.COMMAND_POSITION.format(f"{20:02X}")
    )
    assert device.is_opening() is True
    assert device.is_closing() is False


@pytest.mark.asyncio
async def test_2pm_set_position_passthrough() -> None:
    """Test set_position sends position directly without transformation."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = relay_switch.SwitchbotRelaySwitch2PM(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff"
    )
    device.update_from_advertisement(
        make_advertisement_data(
            ble_device,
            b"\x00\x00\x00\x00\x00\x00",
            SwitchbotModel.RELAY_SWITCH_2PM,
            {
                1: {
                    "switchMode": True,
                    "sequence_number": 99,
                    "isOn": True,
                    "position": 30,
                    "calibration": True,
                    "mode": 0,
                },
                2: {
                    "switchMode": True,
                    "sequence_number": 99,
                    "isOn": False,
                    "position": 30,
                    "calibration": True,
                    "mode": 0,
                },
            },
        )
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()

    await device.set_position(40)
    # position sent directly as-is
    device._send_command.assert_called_with(
        relay_switch.COMMAND_POSITION.format(f"{40:02X}")
    )


def test_2pm_position_property() -> None:
    """Test position property returns value from channel 1."""
    device = create_2pm_device_with_position(position=42)
    assert device.position == 42


def test_2pm_mode_property() -> None:
    """Test mode property returns value from channel 1."""
    device = create_2pm_device_with_position()
    assert device.mode == 0


def test_2pm_update_motion_direction_no_previous() -> None:
    """Test _update_motion_direction with no previous position does nothing."""
    device = create_2pm_device_with_position()
    device._update_motion_direction(True, None, 80)
    assert device.is_opening() is False
    assert device.is_closing() is False


def test_2pm_update_motion_direction_stop() -> None:
    """Test _update_motion_direction with in_motion=False clears both flags."""
    device = create_2pm_device_with_position()
    device._is_opening = True
    device._is_closing = True
    device._update_motion_direction(False, 50, 80)
    assert device.is_opening() is False
    assert device.is_closing() is False


def test_2pm_update_motion_direction_opening() -> None:
    """Test _update_motion_direction detects opening."""
    device = create_2pm_device_with_position()
    device._update_motion_direction(True, 30, 70)
    assert device.is_opening() is True
    assert device.is_closing() is False


def test_2pm_update_motion_direction_closing() -> None:
    """Test _update_motion_direction detects closing."""
    device = create_2pm_device_with_position()
    device._update_motion_direction(True, 70, 30)
    assert device.is_opening() is False
    assert device.is_closing() is True


@pytest.mark.asyncio
async def test_2pm_open_does_not_set_motion_flag_on_failure() -> None:
    """If the open command result fails, _is_opening must remain False."""
    device = create_2pm_device_with_position()
    device._check_command_result = MagicMock(return_value=False)
    result = await device.open()
    assert result is False
    assert device.is_opening() is False
    assert device.is_closing() is False


@pytest.mark.asyncio
async def test_2pm_close_does_not_set_motion_flag_on_failure() -> None:
    """If the close command result fails, _is_closing must remain False."""
    device = create_2pm_device_with_position()
    device._check_command_result = MagicMock(return_value=False)
    result = await device.close()
    assert result is False
    assert device.is_opening() is False
    assert device.is_closing() is False


@pytest.mark.asyncio
async def test_2pm_stop_does_not_clear_motion_flags_on_failure() -> None:
    """If the stop command result fails, the prior motion flags persist."""
    device = create_2pm_device_with_position()
    device._is_opening = True
    device._is_closing = False
    device._check_command_result = MagicMock(return_value=False)
    result = await device.stop()
    assert result is False
    assert device.is_opening() is True
    assert device.is_closing() is False


@pytest.mark.asyncio
async def test_2pm_set_position_does_not_update_direction_on_failure() -> None:
    """If the set_position command result fails, motion flags must not change."""
    device = create_2pm_device_with_position(position=30)
    device._check_command_result = MagicMock(return_value=False)
    result = await device.set_position(80)
    assert result is False
    assert device.is_opening() is False
    assert device.is_closing() is False


def test_parse_common_data_includes_sequence_number() -> None:
    """
    `_parse_common_data` must expose `sequence_number` from raw_data[1].

    Regression test: the key was inadvertently dropped during the 2PM roller
    work, breaking any 1PM `get_basic_info` consumer reading it.
    """
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = relay_switch.SwitchbotRelaySwitch(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff"
    )
    raw_data = bytes(
        [
            0x01,
            0x2A,
            0x80,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x10,
        ]
    )
    parsed = device._parse_common_data(raw_data)
    assert parsed["sequence_number"] == 0x2A


def test_2pm_adv_parses_distinct_per_channel_modes() -> None:
    """
    Channel 1 mode is the lower nibble of mfr_data[9]; channel 2 the upper.

    Regression for the precedence bug `mfr_data[9] & 0b11110000 >> 4` which
    Python parses as `mfr_data[9] & (0b11110000 >> 4)` = `mfr_data[9] & 0x0F`,
    silently returning channel 1's mode for channel 2.
    """
    # mfr_data[9] = 0x53 → lower nibble 3 (channel 1), upper nibble 5 (channel 2)
    mfr_data = bytes(6) + bytes([0x8A, 0xC1, 0x00, 0x53, 0x00, 0x00, 0x00, 0x00, 0x00])
    parsed = process_relay_switch_2pm(None, mfr_data)
    assert parsed[1]["mode"] == 0x3
    assert parsed[2]["mode"] == 0x5
