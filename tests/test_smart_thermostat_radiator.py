from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement
from switchbot.const.climate import ClimateAction, ClimateMode
from switchbot.const.climate import SmartThermostatRadiatorMode as STRMode
from switchbot.devices.device import SwitchbotEncryptedDevice, SwitchbotOperationError
from switchbot.devices.smart_thermostat_radiator import (
    COMMAND_SET_MODE,
    COMMAND_SET_TEMP,
    SwitchbotSmartThermostatRadiator,
)

from . import SMART_THERMOSTAT_RADIATOR_INFO
from .test_adv_parser import AdvTestCase, generate_ble_device


def create_device_for_command_testing(
    adv_info: AdvTestCase,
    init_data: dict | None = None,
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotSmartThermostatRadiator(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=adv_info.modelName
    )
    device.update_from_advertisement(
        make_advertisement_data(ble_device, adv_info, init_data)
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice, adv_info: AdvTestCase, init_data: dict | None = None
):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": adv_info.service_data,
            "data": adv_info.data | init_data,
            "isEncrypted": False,
            "model": adv_info.model,
            "modelFriendlyName": adv_info.modelFriendlyName,
            "modelName": adv_info.modelName,
        }
        | init_data,
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_default_info() -> None:
    device = create_device_for_command_testing(SMART_THERMOSTAT_RADIATOR_INFO)

    assert device.min_temperature == 5.0
    assert device.max_temperature == 35.0
    assert device.preset_mode == STRMode.MANUAL.lname
    assert device.preset_modes == STRMode.get_modes()
    assert device.hvac_mode == ClimateMode.HEAT
    assert device.hvac_modes == {ClimateMode.OFF, ClimateMode.HEAT}
    assert device.hvac_action == ClimateAction.HEATING
    assert device.target_temperature == 35.0
    assert device.current_temperature == 28.0
    assert device.door_open() is False


@pytest.mark.asyncio
async def test_default_info_with_off_mode() -> None:
    device = create_device_for_command_testing(
        SMART_THERMOSTAT_RADIATOR_INFO, {"mode": STRMode.OFF.lname, "isOn": False}
    )
    assert device.hvac_action == ClimateAction.OFF


@pytest.mark.parametrize(
    ("mode", "expected_command"),
    [
        (ClimateMode.OFF, "570100"),
        (ClimateMode.HEAT, COMMAND_SET_MODE[STRMode.COMFORT.lname]),
    ],
)
@pytest.mark.asyncio
async def test_set_hvac_mode_commands(mode, expected_command) -> None:
    device = create_device_for_command_testing(SMART_THERMOSTAT_RADIATOR_INFO)

    await device.set_hvac_mode(mode)
    device._send_command.assert_awaited_with(expected_command)


@pytest.mark.parametrize(
    ("preset_mode", "expected_command"),
    [
        (STRMode.SCHEDULE.lname, COMMAND_SET_MODE[STRMode.SCHEDULE.lname]),
        (STRMode.MANUAL.lname, COMMAND_SET_MODE[STRMode.MANUAL.lname]),
        (STRMode.OFF.lname, COMMAND_SET_MODE[STRMode.OFF.lname]),
        (STRMode.ECONOMIC.lname, COMMAND_SET_MODE[STRMode.ECONOMIC.lname]),
        (STRMode.COMFORT.lname, COMMAND_SET_MODE[STRMode.COMFORT.lname]),
        (STRMode.FAST_HEATING.lname, COMMAND_SET_MODE[STRMode.FAST_HEATING.lname]),
    ],
)
@pytest.mark.asyncio
async def test_set_preset_mode_commands(preset_mode, expected_command) -> None:
    device = create_device_for_command_testing(SMART_THERMOSTAT_RADIATOR_INFO)

    await device.set_preset_mode(preset_mode)
    device._send_command.assert_awaited_with(expected_command)


@pytest.mark.asyncio
async def test_set_target_temperature_command() -> None:
    device = create_device_for_command_testing(SMART_THERMOSTAT_RADIATOR_INFO)

    await device.set_target_temperature(22.5)
    device._send_command.assert_awaited_with(
        COMMAND_SET_TEMP[STRMode.MANUAL.lname].format(temp=225)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "match"),
    [
        (STRMode.OFF.lname, "Cannot set temperature when mode is OFF."),
        (STRMode.FAST_HEATING.lname, "Fast Heating mode defaults to max temperature."),
    ],
)
async def test_set_target_temperature_with_invalid_mode(mode, match) -> None:
    device = create_device_for_command_testing(
        SMART_THERMOSTAT_RADIATOR_INFO, {"mode": mode}
    )

    with pytest.raises(SwitchbotOperationError, match=match):
        await device.set_target_temperature(22.5)


@pytest.mark.asyncio
async def test_get_basic_info_none() -> None:
    device = create_device_for_command_testing(SMART_THERMOSTAT_RADIATOR_INFO)
    device._get_basic_info = AsyncMock(return_value=None)

    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "result"),
    [
        (
            b"\x01d\x08>\x14\x80\xe6\x00(\x82\xbe\x00T\x00\x82\x00\x00",
            [
                100,
                0.8,
                62,
                "off",
                "comfort",
                23.0,
                4.0,
                13.0,
                19.0,
                0,
                False,
                13.0,
                False,
            ],
        ),
        (
            b"\x01d\x08>#\x80\xf0\x00(\x82\xbe\x00T\x00\x82\x00\x00",
            [
                100,
                0.8,
                62,
                "comfort",
                "economic",
                24.0,
                4.0,
                13.0,
                19.0,
                0,
                False,
                13.0,
                False,
            ],
        ),
    ],
)
async def test_get_basic_info_parsing(basic_info, result) -> None:
    device = create_device_for_command_testing(SMART_THERMOSTAT_RADIATOR_INFO)
    device._get_basic_info = AsyncMock(return_value=basic_info)

    info = await device.get_basic_info()
    assert info["battery"] == result[0]
    assert info["firmware"] == result[1]
    assert info["hardware"] == result[2]
    assert info["last_mode"] == result[3]
    assert info["mode"] == result[4]
    assert info["temperature"] == result[5]
    assert info["manual_target_temp"] == result[6]
    assert info["comfort_target_temp"] == result[7]
    assert info["economic_target_temp"] == result[8]
    assert info["fast_heat_time"] == result[9]
    assert info["child_lock"] == result[10]
    assert info["target_temp"] == result[11]
    assert info["door_open"] == result[12]


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await SwitchbotSmartThermostatRadiator.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
        model=SMART_THERMOSTAT_RADIATOR_INFO.modelName,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        SMART_THERMOSTAT_RADIATOR_INFO.modelName,
    )

    assert result is True
