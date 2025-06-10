from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotEncryptedDevice, SwitchbotModel
from switchbot.devices import relay_switch
from switchbot.devices.device import _merge_data as merge_data

from .test_adv_parser import generate_ble_device

common_params = [
    (b";\x00\x00\x00", SwitchbotModel.RELAY_SWITCH_1),
    (b"<\x00\x00\x00", SwitchbotModel.RELAY_SWITCH_1PM),
    (b">\x00\x00\x00", SwitchbotModel.GARAGE_DOOR_OPENER),
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
    device_class = (
        relay_switch.SwitchbotRelaySwitch2PM
        if model == SwitchbotModel.RELAY_SWITCH_2PM
        else relay_switch.SwitchbotRelaySwitch
    )
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
async def test_turn_on_2PM(common_parametrize_2pm, init_data):
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
async def test_turn_off_2PM(common_parametrize_2pm, init_data):
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
async def test_turn_toggle_2PM(common_parametrize_2pm):
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
async def test_get_switch_mode_2PM(common_parametrize_2pm):
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
async def test_get_basic_info_2PM(common_parametrize_2pm, info_data, result):
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
async def test_basic_info_exceptions_2PM(common_parametrize_2pm, info_data):
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
async def test_get_parsed_data_2PM(common_parametrize_2pm):
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
async def test_turn_on(rawAdvData, model):
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
async def test_turn_off(rawAdvData, model):
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
async def test_toggle(rawAdvData, model):
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
async def test_get_basic_info_garage_door_opener(rawAdvData, model, info_data):
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.RELAY_SWITCH_1,
        SwitchbotModel.RELAY_SWITCH_1PM,
        SwitchbotModel.GARAGE_DOOR_OPENER,
        SwitchbotModel.RELAY_SWITCH_2PM,
    ],
)
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify, model):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await relay_switch.SwitchbotRelaySwitch.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
        model=model,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        model,
    )

    assert result is True


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
def test_merge_data(old_data, new_data, expected_result):
    """Test merging of data dictionaries."""
    result = merge_data(old_data, new_data)
    assert result == expected_result
