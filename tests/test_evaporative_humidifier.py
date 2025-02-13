import datetime
from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.adv_parsers.humidifier import process_evaporative_humidifier
from switchbot.const.evaporative_humidifier import HumidifierMode, HumidifierWaterLevel
from switchbot.devices import evaporative_humidifier

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
                "target_humidity": None,
                "child_lock": False,
                "over_humidify_protection": True,
                "tank_removed": False,
                "tilted_alert": False,
                "filter_missing": False,
                "humidity": 51,
                "temperature": 16.8,
                "filter_run_time": datetime.timedelta(days=3, seconds=57600),
                "filter_alert": False,
                "water_level": HumidifierWaterLevel.LOW,
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
async def test_process_advertisement():
    data = process_evaporative_humidifier(
        b"#\x00\x00\x15\x1c\x00",
        b"\xd4\x8cIU\x95\xb2\x08\x06\x88\xb3\x90\x81\x00X\x00X2",
    )

    assert data == {
        "isOn": False,
        "mode": None,
        "target_humidity": None,
        "child_lock": False,
        "over_humidify_protection": None,
        "tank_removed": False,
        "tilted_alert": False,
        "filter_missing": False,
        "humidity": 51,
        "temperature": 16.8,
        "filter_run_time": datetime.timedelta(days=3, seconds=57600),
        "filter_alert": False,
        "water_level": HumidifierWaterLevel.LOW,
    }


@pytest.mark.asyncio
async def test_process_advertisement_empty():
    data = process_evaporative_humidifier(None, None)

    assert data == {
        "isOn": None,
        "mode": None,
        "target_humidity": None,
        "child_lock": None,
        "over_humidify_protection": None,
        "tank_removed": None,
        "tilted_alert": None,
        "filter_missing": None,
        "humidity": None,
        "temperature": None,
        "filter_run_time": None,
        "filter_alert": None,
        "water_level": None,
    }


@pytest.mark.asyncio
async def test_turn_on():
    device = create_device_for_command_testing({"isOn": False})
    device._send_command = AsyncMock(return_value=b"\x01")

    assert device.is_on() is False
    await device.turn_on()
    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    device = create_device_for_command_testing({"isOn": True})
    device._send_command = AsyncMock(return_value=b"\x01")

    assert device.is_on() is True
    await device.turn_off()
    assert device.is_on() is False


@pytest.mark.asyncio
async def test_set_mode():
    device = create_device_for_command_testing(
        {"isOn": True, "mode": HumidifierMode.LOW}
    )
    device._send_command = AsyncMock(return_value=b"\x01")

    assert device.get_mode() is HumidifierMode.LOW
    await device.set_mode(HumidifierMode.AUTO)
    assert device.get_mode() is HumidifierMode.AUTO

    await device.set_mode(HumidifierMode.TARGET_HUMIDITY, 60)
    assert device.get_mode() is HumidifierMode.TARGET_HUMIDITY
    assert device.get_target_humidity() == 60

    await device.set_mode(HumidifierMode.DRYING_FILTER)
    assert device.get_mode() is HumidifierMode.DRYING_FILTER

    with pytest.raises(ValueError):
        await device.set_mode(0)

    with pytest.raises(TypeError):
        await device.set_mode(HumidifierMode.TARGET_HUMIDITY)


@pytest.mark.asyncio
async def test_set_child_lock():
    device = create_device_for_command_testing({"child_lock": False})
    device._send_command = AsyncMock(return_value=b"\x01")

    assert device.is_child_lock_enabled() is False
    await device.set_child_lock(True)
    assert device.is_child_lock_enabled() is True


@pytest.mark.asyncio
async def test_start_drying_filter():
    device = create_device_for_command_testing(
        {"isOn": True, "mode": HumidifierMode.AUTO}
    )
    device._send_command = AsyncMock(return_value=b"\x01")

    assert device.get_mode() is HumidifierMode.AUTO
    await device.start_drying_filter()
    assert device.get_mode() is HumidifierMode.DRYING_FILTER


@pytest.mark.asyncio
async def test_stop_drying_filter():
    device = create_device_for_command_testing(
        {"isOn": True, "mode": HumidifierMode.DRYING_FILTER}
    )
    device._send_command = AsyncMock(return_value=b"\x00")

    assert device.is_on() is True
    assert device.get_mode() is HumidifierMode.DRYING_FILTER
    await device.stop_drying_filter()
    assert device.is_on() is False
    assert device.get_mode() is None


@pytest.mark.asyncio
async def test_attributes():
    device = create_device_for_command_testing()
    device._send_command = AsyncMock(return_value=b"\x01")

    assert device.is_over_humidify_protection_enabled() is True
    assert device.is_tank_removed() is False
    assert device.is_filter_missing() is False
    assert device.is_filter_alert_on() is False
    assert device.is_tilted_alert_on() is False
    assert device.get_water_level() is HumidifierWaterLevel.LOW
    assert device.get_filter_run_time() == datetime.timedelta(days=3, seconds=57600)
    assert device.get_humidity() == 51
    assert device.get_temperature() == 16.8
