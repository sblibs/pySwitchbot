import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import (
    HumidifierAction,
    HumidifierMode,
    HumidifierWaterLevel,
    SwitchBotAdvertisement,
    SwitchbotModel,
)
from switchbot.devices import evaporative_humidifier
from switchbot.devices.device import SwitchbotEncryptedDevice, SwitchbotOperationError

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(init_data: dict | None = None):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    evaporative_humidifier_device = (
        evaporative_humidifier.SwitchbotEvaporativeHumidifier(
            ble_device, "ff", "ffffffffffffffffffffffffffffffff"
        )
    )
    evaporative_humidifier_device.update_from_advertisement(
        make_advertisement_data(ble_device, init_data)
    )
    evaporative_humidifier_device._send_command = AsyncMock()
    evaporative_humidifier_device._check_command_result = MagicMock()
    evaporative_humidifier_device.update = AsyncMock()
    return evaporative_humidifier_device


def make_advertisement_data(ble_device: BLEDevice, init_data: dict | None = None):
    if init_data is None:
        init_data = {}
    """Set advertisement data with defaults."""
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"#\x00\x00\x15\x1c\x00",
            "data": {
                "isOn": False,
                "mode": None,
                "target_humidity": 52,
                "child_lock": False,
                "over_humidify_protection": True,
                "tank_removed": False,
                "tilted_alert": False,
                "filter_missing": False,
                "is_meter_binded": True,
                "humidity": 51,
                "temperature": 16.8,
                "temp": {"c": 16.8, "f": 62.24},
                "filter_run_time": datetime.timedelta(days=3, seconds=57600),
                "filter_alert": False,
                "water_level": "medium",
            }
            | init_data,
            "isEncrypted": False,
            "model": "#",
            "modelFriendlyName": "Evaporative Humidifier",
            "modelName": SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_turn_on():
    """Test the turn_on method."""
    device = create_device_for_command_testing({"isOn": True})
    await device.turn_on()
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    """Test the turn_off method."""
    device = create_device_for_command_testing({"isOn": False})
    await device.turn_off()
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_get_basic_is_none():
    """Test the get_basic_info when it returns None."""
    device = create_device_for_command_testing()
    device._get_basic_info = AsyncMock(return_value=None)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "result"),
    [
        (
            bytearray(b"\x01\x86\x88\xb1\x98\x82\x00\x1e\x00\x88-\xc4\xff\xff \n\x07"),
            [
                True,
                HumidifierMode(6),
                True,
                False,
                False,
                False,
                False,
                True,
                49,
                24.8,
                24.8,
                76.64,
                "medium",
                30,
                45,
            ],
        ),
        (
            bytearray(b"\x01\x08 \xb1\x98r\x00\x1e\x00\x89-\xc4\xff\xff\x00\x00\x00"),
            [
                False,
                HumidifierMode(8),
                False,
                True,
                False,
                False,
                False,
                True,
                49,
                24.7,
                24.7,
                76.46,
                "medium",
                30,
                45,
            ],
        ),
    ],
)
async def test_get_basic_info(basic_info, result):
    """Test the get_basic_info method."""
    device = create_device_for_command_testing()
    device._get_basic_info = AsyncMock(return_value=basic_info)

    info = await device.get_basic_info()
    assert info["isOn"] is result[0]
    assert info["mode"] == result[1]
    assert info["over_humidify_protection"] is result[2]
    assert info["child_lock"] is result[3]
    assert info["tank_removed"] is result[4]
    assert info["tilted_alert"] is result[5]
    assert info["filter_missing"] is result[6]
    assert info["is_meter_binded"] is result[7]
    assert info["humidity"] == result[8]
    assert info["temperature"] == result[9]
    assert info["temp"]["c"] == result[10]
    assert info["temp"]["f"] == result[11]
    assert info["water_level"] == result[12]
    assert info["filter_run_time"] == result[13]
    assert info["target_humidity"] == result[14]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("err_msg", "mode", "water_level"),
    [
        (
            "Target humidity can only be set in target humidity mode or sleep mode",
            HumidifierMode.AUTO,
            "low",
        ),
        (
            "Cannot perform operation when water tank is empty",
            HumidifierMode.TARGET_HUMIDITY,
            "empty",
        ),
    ],
)
async def test_set_target_humidity_with_invalid_conditions(err_msg, mode, water_level):
    """Test setting target humidity with invalid mode."""
    device = create_device_for_command_testing()
    device.get_mode = MagicMock(return_value=mode)
    device.get_water_level = MagicMock(return_value=water_level)
    with pytest.raises(SwitchbotOperationError, match=err_msg):
        await device.set_target_humidity(45)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("err_msg", "mode", "water_level", "is_meter_binded", "target_humidity"),
    [
        (
            "Cannot perform operation when water tank is empty",
            HumidifierMode.TARGET_HUMIDITY,
            "empty",
            True,
            45,
        ),
        (
            "Cannot set target humidity or auto mode when meter is not binded",
            HumidifierMode.TARGET_HUMIDITY,
            "medium",
            False,
            45,
        ),
        (
            "Target humidity must be set before switching to target humidity mode or sleep mode",
            HumidifierMode.TARGET_HUMIDITY,
            "medium",
            True,
            None,
        ),
    ],
)
async def test_set_mode_with_invalid_conditions(
    err_msg, mode, water_level, is_meter_binded, target_humidity
):
    """Test setting target humidity with invalid mode."""
    device = create_device_for_command_testing()
    device.get_water_level = MagicMock(return_value=water_level)
    device.is_meter_binded = MagicMock(return_value=is_meter_binded)
    device.get_target_humidity = MagicMock(return_value=target_humidity)
    with pytest.raises(SwitchbotOperationError, match=err_msg):
        await device.set_mode(mode)


@pytest.mark.asyncio
async def test_set_target_humidity():
    """Test setting target humidity."""
    device = create_device_for_command_testing()
    device.get_mode = MagicMock(return_value=HumidifierMode.TARGET_HUMIDITY)

    await device.set_target_humidity(45)
    device._send_command.assert_awaited_once_with("570f430202002d")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "command"),
    [
        (HumidifierMode.TARGET_HUMIDITY, "570f430202002d"),
        (HumidifierMode.AUTO, "570f4302040000"),
        (HumidifierMode.SLEEP, "570f430203002d"),
        (HumidifierMode.DRYING_FILTER, "570f43010108"),
    ],
)
async def test_set_mode(mode, command):
    """Test setting mode."""
    device = create_device_for_command_testing()
    device.get_target_humidity = MagicMock(return_value=45)

    await device.set_mode(mode)
    device._send_command.assert_awaited_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("init_data", "result"),
    [
        (
            {"isOn": False, "mode": HumidifierMode.AUTO},
            [False, HumidifierMode.AUTO, HumidifierAction.OFF],
        ),
        (
            {"isOn": True, "mode": HumidifierMode.TARGET_HUMIDITY},
            [True, HumidifierMode.TARGET_HUMIDITY, HumidifierAction.HUMIDIFYING],
        ),
        (
            {"isOn": True, "mode": HumidifierMode.DRYING_FILTER},
            [True, HumidifierMode.DRYING_FILTER, HumidifierAction.DRYING],
        ),
    ],
)
async def test_status_from_process_adv(init_data, result):
    """Test status from process advertisement."""
    device = create_device_for_command_testing(init_data)

    assert device.is_on() is result[0]
    assert device.get_mode() is result[1]
    assert device.is_child_lock_enabled() is False
    assert device.is_over_humidify_protection_enabled() is True
    assert device.is_tank_removed() is False
    assert device.is_filter_missing() is False
    assert device.is_filter_alert_on() is False
    assert device.is_tilted_alert_on() is False
    assert device.get_water_level() == "medium"
    assert device.get_filter_run_time() == datetime.timedelta(days=3, seconds=57600)
    assert device.get_target_humidity() == 52
    assert device.get_humidity() == 51
    assert device.get_temperature() == 16.8
    assert device.get_action() == result[2]
    assert device.is_meter_binded() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enabled", "command"),
    [
        (True, "570f430501"),
        (False, "570f430500"),
    ],
)
async def test_set_child_lock(enabled, command):
    """Test setting child lock."""
    device = create_device_for_command_testing()
    await device.set_child_lock(enabled)
    device._send_command.assert_awaited_once_with(command)


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await evaporative_humidifier.SwitchbotEvaporativeHumidifier.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
    )

    assert result is True


def test_evaporative_humidifier_modes():
    assert HumidifierMode.get_modes() == [
        "high",
        "medium",
        "low",
        "quiet",
        "target_humidity",
        "sleep",
        "auto",
        "drying_filter",
    ]


def test_evaporative_humidifier_water_levels():
    assert HumidifierWaterLevel.get_levels() == [
        "empty",
        "low",
        "medium",
        "high",
    ]
