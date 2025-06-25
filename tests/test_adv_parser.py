from __future__ import annotations

import datetime
from typing import Any

import pytest
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from switchbot import HumidifierMode, SwitchbotModel
from switchbot.adv_parser import parse_advertisement_data
from switchbot.const.lock import LockStatus
from switchbot.models import SwitchBotAdvertisement

from . import AdvTestCase

ADVERTISEMENT_DATA_DEFAULTS = {
    "local_name": "",
    "manufacturer_data": {},
    "service_data": {},
    "service_uuids": [],
    "rssi": -127,
    "platform_data": ((),),
    "tx_power": -127,
}

BLE_DEVICE_DEFAULTS = {
    "name": None,
    "rssi": -127,
    "details": None,
}


def generate_ble_device(
    address: str | None = None,
    name: str | None = None,
    details: Any | None = None,
    rssi: int | None = None,
    **kwargs: Any,
) -> BLEDevice:
    """Generate a BLEDevice with defaults."""
    new = kwargs.copy()
    if address is not None:
        new["address"] = address
    if name is not None:
        new["name"] = name
    if details is not None:
        new["details"] = details
    if rssi is not None:
        new["rssi"] = rssi
    for key, value in BLE_DEVICE_DEFAULTS.items():
        new.setdefault(key, value)
    return BLEDevice(**new)


def generate_advertisement_data(**kwargs: Any) -> AdvertisementData:
    """Generate advertisement data with defaults."""
    new = kwargs.copy()
    for key, value in ADVERTISEMENT_DATA_DEFAULTS.items():
        new.setdefault(key, value)
    return AdvertisementData(**new)


def test_parse_advertisement_data_curtain():
    """Test parse_advertisement_data for curtain."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0X\x00\x11\x04"},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0X\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 88,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def test_parse_advertisement_data_curtain_passive():
    """Test parse_advertisement_data for curtain passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "calibration": None,
                "battery": None,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=False,
    )


def test_parse_advertisement_data_curtain_passive_12_bytes():
    """Test parse_advertisement_data for curtain passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04\x00"},
        service_data={},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "calibration": None,
                "battery": None,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=False,
    )


def test_parse_advertisement_data_curtain_position_zero():
    """Test parse_advertisement_data for curtain position zero."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={89: b"\xc1\xc7'}U\xab"},
        service_data={"00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0\xced\x11\x04"},
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-52,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xd0\xced\x11\x04",
            "data": {
                "calibration": True,
                "battery": 78,
                "inMotion": False,
                "position": 0,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-52,
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_position_100():
    """Test parse_advertisement_data with firmware six for curtain position 100."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xf5\x98\x94\x08\xa0\xe7",
            2409: b'\xf5\x98\x94\x08\xa0\xe7\x9b\x0f\x00"\x04',
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0H\x00\x12\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b'c\xc0G\x00"\x04',
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-62,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b'c\xc0G\x00"\x04',
            "data": {
                "calibration": True,
                "battery": 71,
                "inMotion": False,
                "position": 100,
                "lightLevel": 2,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-62,
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_position_100_other_rssi():
    """Test parse_advertisement_data with firmware six for curtain position 100 other rssi."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xf5\x98\x94\x08\xa0\xe7",
            2409: b'\xf5\x98\x94\x08\xa0\xe7\xa5\x0fc"\x04',
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0H\x00\x12\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b'c\xc0Gc"\x04',
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b'c\xc0Gc"\x04',
            "data": {
                "calibration": True,
                "battery": 71,
                "inMotion": False,
                "position": 1,
                "lightLevel": 2,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parse_advertisement_data_curtain_fully_closed():
    """Test parse_advertisement_data with firmware six fully closed."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={2409: b"\xc1\xc7'}U\xab\"\x0fd\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0Sd\x11\x04"},
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=1,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0Sd\x11\x04",
            "data": {
                "calibration": True,
                "battery": 83,
                "inMotion": False,
                "position": 0,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=1,
        active=True,
    )


def test_parse_advertisement_data_curtain_fully_open():
    """Test parse_advertisement_data with firmware six fully open."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={2409: b"\xc1\xc7'}U\xab%\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0S\x00\x11\x04"},
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=1,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0S\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 83,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=1,
        active=True,
    )


def test_parse_advertisement_data_curtain3():
    """Test parse_advertisement_data for curtain 3."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xaa\xbb\xcc\xdd\xee\xff\xf7\x07\x00\x11\x04\x00\x49"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"{\xc0\x49\x00\x11\x04"},
        rssi=-80,
    )

    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"{\xc0\x49\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 73,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "{",
            "modelFriendlyName": "Curtain 3",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def test_parse_advertisement_data_curtain3_passive():
    """Test parse_advertisement_data for curtain passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xaa\xbb\xcc\xdd\xee\xff\xf7\x07\x00\x11\x04\x00\x49"
        },
        service_data={},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "calibration": None,
                "battery": 73,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=False,
    )


def test_parse_advertisement_data_contact():
    """Test parse_advertisement_data for the contact sensor."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d@d\x05\x00u\x00\xf8\x12"
        },
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"d@d\x05\x00u\x00\xf8\x12",
            "data": {
                "button_count": 2,
                "contact_open": True,
                "contact_timeout": True,
                "is_light": True,
                "battery": 100,
                "motion_detected": True,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def test_parse_advertisement_data_empty():
    """Test parse_advertisement_data with empty data does not blow up."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2403: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b""},
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result is None


def test_new_bot_firmware():
    """Test parsing adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={89: b"\xd8.\xad\xcd\r\x85"},
        service_data={"00000d00-0000-1000-8000-00805f9b34fb": b"H\x10\xe1"},
        service_uuids=["CBA20D00-224D-11E6-9FB8-0002A5D5C51B"],
        rssi=-90,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"H\x10\xe1",
            "data": {"switchMode": False, "isOn": False, "battery": 97},
            "model": "H",
            "isEncrypted": False,
            "modelFriendlyName": "Bot",
            "modelName": SwitchbotModel.BOT,
        },
        device=ble_device,
        rssi=-90,
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_fully_closed():
    """Test parse_advertisement_data with firmware six fully closed."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xcc\xf4\xc4\xf9\xacl",
            2409: b"\xcc\xf4\xc4\xf9\xacl\xeb\x0fd\x12\x04",
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0Yd\x11\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0dd\x12\x04",
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-2,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0dd\x12\x04",
            "data": {
                "calibration": True,
                "battery": 100,
                "inMotion": False,
                "position": 0,
                "lightLevel": 1,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-2,
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_fully_open():
    """Test parse_advertisement_data with firmware six fully open."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xcc\xf4\xc4\xf9\xacl",
            2409: b"\xcc\xf4\xc4\xf9\xacl\xe2\x0f\x00\x12\x04",
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0Yd\x11\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0d\x00\x12\x04",
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-2,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0d\x00\x12\x04",
            "data": {
                "calibration": True,
                "battery": 100,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-2,
        active=True,
    )


def test_contact_sensor_mfr():
    """Test parsing adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=FA,\x00F\x01\x8f\xc4"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d\x00\xda\x04\x00F\x01\x8f\xc4"
        },
        tx_power=-127,
        rssi=-70,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": True,
                "contact_timeout": True,
                "is_light": False,
                "motion_detected": False,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d\x00\xda\x04\x00F\x01\x8f\xc4",
        },
        device=ble_device,
        rssi=-70,
        active=True,
    )


def test_contact_sensor_mfr_no_service_data():
    """Test contact sensor with passive data only."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=FA,\x00F\x01\x8f\xc4"},
        service_data={},
        tx_power=-127,
        rssi=-70,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    # Passive detection of contact sensor is not supported
    # anymore since the Switchbot Curtain v3 was released
    # which uses the heuristics for the contact sensor.
    assert result is None


def test_contact_sensor_srv():
    """Test parsing adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d\x00\xda\x04\x00F\x01\x8f\xc4"
        },
        tx_power=-127,
        rssi=-70,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": True,
                "contact_timeout": True,
                "is_light": False,
                "motion_detected": False,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d\x00\xda\x04\x00F\x01\x8f\xc4",
        },
        device=ble_device,
        rssi=-70,
        active=True,
    )


def test_contact_sensor_open():
    """Test parsing mfr adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=F\x84\x9c\x00\x17\x00QD"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d@\xda\x02\x00\x17\x00QD"
        },
        tx_power=-127,
        rssi=-59,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": True,
                "contact_timeout": False,
                "is_light": False,
                "motion_detected": True,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d@\xda\x02\x00\x17\x00QD",
        },
        device=ble_device,
        rssi=-59,
        active=True,
    )


def test_contact_sensor_closed():
    """Test parsing mfr adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=F\x89\x8c\x00+\x00\x19\x84"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d@\xda\x00\x00+\x00\x19\x84"
        },
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": False,
                "contact_timeout": False,
                "is_light": False,
                "motion_detected": True,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d@\xda\x00\x00+\x00\x19\x84",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_switchbot_passive():
    """Test parsing switchbot as passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={89: bytes.fromhex("d51cfb397856")},
        service_data={},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.BOT)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "switchMode": None,
                "isOn": None,
            },
            "isEncrypted": False,
            "model": "H",
            "modelFriendlyName": "Bot",
            "modelName": SwitchbotModel.BOT,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-50,
        active=False,
    )


def test_bulb_active():
    """Test parsing bulb as active."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\x84\xf7\x03\xb4\xcbz\x03\xe4!\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"u\x00d"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "brightness": 100,
                "color_mode": 1,
                "delay": False,
                "isOn": True,
                "loop_index": 0,
                "preset": False,
                "sequence_number": 3,
                "speed": 0,
            },
            "isEncrypted": False,
            "model": "u",
            "modelFriendlyName": "Color Bulb",
            "modelName": SwitchbotModel.COLOR_BULB,
            "rawAdvData": b"u\x00d",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wosensor_passive_and_active():
    """Test parsing wosensor as passive with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xd7\xc1}]\xebC\xde\x03\x06\x985"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"T\x00\xe4\x06\x985"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "T",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER,
            "rawAdvData": b"T\x00\xe4\x06\x985",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wosensor_active():
    """Test parsing wosensor with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"T\x00\xe4\x06\x985"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "T",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER,
            "rawAdvData": b"T\x00\xe4\x06\x985",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wosensor_passive_only():
    """Test parsing wosensor with only passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xd7\xc1}]\xebC\xde\x03\x06\x985"},
        service_data={},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.METER)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "T",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-50,
        active=False,
    )


def test_wosensor_active_zero_data():
    """Test parsing wosensor with active data but all values are zero."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"T\x00\x00\x00\x00\x00"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {},
            "isEncrypted": False,
            "model": "T",
            "rawAdvData": b"T\x00\x00\x00\x00\x00",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wohub2_passive_and_active():
    """Test parsing wosensor as passive with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xaa\xbb\xcc\xdd\xee\xff\x00\xfffT\x1a\xf1\x82\x07\x9a2\x00"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"v\x00"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "fahrenheit": False,
                "humidity": 50,
                "lightLevel": 2,
                "illuminance": 10,
                "temp": {"c": 26.7, "f": 80.06},
                "temperature": 26.7,
            },
            "isEncrypted": False,
            "model": "v",
            "modelFriendlyName": "Hub 2",
            "modelName": SwitchbotModel.HUB2,
            "rawAdvData": b"v\x00",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_woiosensor_passive_and_active():
    """Test parsing woiosensor as passive with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xaa\xbb\xcc\xdd\xee\xff\xe0\x0f\x06\x985\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"w\x00\xe4"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "w",
            "modelFriendlyName": "Indoor/Outdoor Meter",
            "modelName": SwitchbotModel.IO_METER,
            "rawAdvData": b"w\x00\xe4",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_woiosensor_passive_only():
    """Test parsing woiosensor with only passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xaa\xbb\xcc\xdd\xee\xff\xe0\x0f\x06\x985\x00"},
        service_data={},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.IO_METER)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "w",
            "modelFriendlyName": "Indoor/Outdoor Meter",
            "modelName": SwitchbotModel.IO_METER,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-50,
        active=False,
    )


def test_motion_sensor_clear():
    """Test parsing motion sensor with clear data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIj\x1c\x00f"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s\x00\xe2\x00f\x01"},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": False,
                "led": 0,
                "light_intensity": 1,
                "motion_detected": False,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s\x00\xe2\x00f\x01",
        },
        device=ble_device,
        rssi=-87,
        active=True,
    )


def test_motion_sensor_clear_passive():
    """Test parsing motion sensor with clear data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIj\x1c\x00f"},
        service_data={},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "iot": None,
                "is_light": False,
                "led": None,
                "light_intensity": None,
                "motion_detected": False,
                "sense_distance": None,
                "tested": None,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-87,
        active=False,
    )


def test_motion_sensor_motion():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIi\\\x008"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s@\xe2\x008\x01"},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": False,
                "led": 0,
                "light_intensity": 1,
                "motion_detected": True,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s@\xe2\x008\x01",
        },
        device=ble_device,
        rssi=-87,
        active=True,
    )


def test_motion_sensor_motion_passive():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIi\\\x008"},
        service_data={},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "iot": None,
                "is_light": False,
                "led": None,
                "light_intensity": None,
                "motion_detected": True,
                "sense_distance": None,
                "tested": None,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-87,
        active=False,
    )


def test_motion_sensor_is_light_passive():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIs,\x04g"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s\x00\xe2\x04g\x02"},
        tx_power=-127,
        rssi=-93,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": True,
                "led": 0,
                "light_intensity": 2,
                "motion_detected": False,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s\x00\xe2\x04g\x02",
        },
        device=ble_device,
        rssi=-93,
        active=True,
    )


def test_motion_sensor_is_light_active():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s\x00\xe2\x04g\x02"},
        tx_power=-127,
        rssi=-93,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": True,
                "led": 0,
                "light_intensity": 2,
                "motion_detected": False,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s\x00\xe2\x04g\x02",
        },
        device=ble_device,
        rssi=-93,
        active=True,
    )


def test_motion_with_light_detected():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIvl\x00,"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s@\xe2\x00,\x02"},
        tx_power=-127,
        rssi=-84,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": True,
                "led": 0,
                "light_intensity": 2,
                "motion_detected": True,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s@\xe2\x00,\x02",
        },
        device=ble_device,
        rssi=-84,
        active=True,
    )


def test_meter_pro_active() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeR\xdd\x84\x06d\x08\x97,\x00\x05"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"4\x00d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 44,
                "temp": {"c": 23.8, "f": 74.84},
                "temperature": 23.8,
            },
            "isEncrypted": False,
            "model": "4",
            "modelFriendlyName": "Meter Pro",
            "modelName": SwitchbotModel.METER_PRO,
            "rawAdvData": b"4\x00d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_meter_pro_passive() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeR\xdd\x84\x06d\x08\x97,\x00\x05"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.METER_PRO)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": False,
                "humidity": 44,
                "temp": {"c": 23.8, "f": 74.84},
                "temperature": 23.8,
            },
            "isEncrypted": False,
            "model": "4",
            "modelFriendlyName": "Meter Pro",
            "modelName": SwitchbotModel.METER_PRO,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_meter_pro_c_active() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xb0\xe9\xfeT2\x15\xb7\xe4\x07\x9b\xa4\x007\x02\xd5\x00"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"5\x00d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": True,
                "humidity": 36,
                "temp": {"c": 27.7, "f": 81.86},
                "temperature": 27.7,
                "co2": 725,
            },
            "isEncrypted": False,
            "model": "5",
            "modelFriendlyName": "Meter Pro CO2",
            "modelName": SwitchbotModel.METER_PRO_C,
            "rawAdvData": b"5\x00d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_meter_pro_c_passive() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xb0\xe9\xfeT2\x15\xb7\xe4\x07\x9b\xa4\x007\x02\xd5\x00"
        },
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.METER_PRO_C)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": True,
                "humidity": 36,
                "temp": {"c": 27.7, "f": 81.86},
                "temperature": 27.7,
                "co2": 725,
            },
            "isEncrypted": False,
            "model": "5",
            "modelFriendlyName": "Meter Pro CO2",
            "modelName": SwitchbotModel.METER_PRO_C,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_parse_advertisement_data_keypad():
    """Test parse_advertisement_data for the keypad."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xeb\x13\x02\xe6#\x0f\x8fd\x00\x00\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"y\x00d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.KEYPAD)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {"attempt_state": 143, "battery": 100},
            "isEncrypted": False,
            "model": "y",
            "modelFriendlyName": "Keypad",
            "modelName": SwitchbotModel.KEYPAD,
            "rawAdvData": b"y\x00d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_leak_active():
    """Test parse_advertisement_data for the leak detector."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc4407Lz\x18N\x98g^\x94Q<\x05\x00\x00\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"&\x00N"},
        rssi=-72,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LEAK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "leak": False,
                "tampered": False,
                "battery": 78,
                "low_battery": False,
            },
            "isEncrypted": False,
            "model": "&",
            "modelFriendlyName": "Leak Detector",
            "modelName": SwitchbotModel.LEAK,
            "rawAdvData": b"&\x00N",
        },
        device=ble_device,
        rssi=-72,
        active=True,
    )


def test_leak_passive():
    """Test parse_advertisement_data for the leak detector."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc4407Lz\x18N\x98g^\x94Q<\x05\x00\x00\x00\x00"},
        rssi=-72,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LEAK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {},
            "isEncrypted": False,
            "model": "&",
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-72,
        active=False,
    )


def test_leak_no_leak_detected():
    """Test parse_advertisement_data for the leak detector."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xc4407LzJd\x98ga\xc4\n<\x05\x00\x00\x00\x00"
        },  # no leak, batt
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"&\x00d"},
        rssi=-73,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LEAK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "leak": False,
                "tampered": False,
                "battery": 100,
                "low_battery": False,
            },
            "isEncrypted": False,
            "model": "&",
            "modelFriendlyName": "Leak Detector",
            "modelName": SwitchbotModel.LEAK,
            "rawAdvData": b"&\x00d",
        },
        device=ble_device,
        rssi=-73,
        active=True,
    )


def test_leak_leak_detected():
    """Test parse_advertisement_data for the leak detector."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xc4407LzGd\xf9ga\xc4\x08<\x05\x00\x00\x00\x00"
        },  # leak, batt
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"&\x00d"},
        rssi=-73,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LEAK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "leak": True,
                "tampered": False,
                "battery": 100,
                "low_battery": False,
            },
            "isEncrypted": False,
            "model": "&",
            "modelFriendlyName": "Leak Detector",
            "modelName": SwitchbotModel.LEAK,
            "rawAdvData": b"&\x00d",
        },
        device=ble_device,
        rssi=-73,
        active=True,
    )


def test_leak_low_battery():
    """Test parse_advertisement_data for the leak detector."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xc4407Lz\x02\t\x98\x00\x00\x00\x00<\x05\x00\x00\x00\x00"
        },  # no leak, low battery
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"&\x00d"},
        rssi=-73,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LEAK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "leak": False,
                "tampered": False,
                "battery": 9,
                "low_battery": False,
            },
            "isEncrypted": False,
            "model": "&",
            "modelFriendlyName": "Leak Detector",
            "modelName": SwitchbotModel.LEAK,
            "rawAdvData": b"&\x00d",
        },
        device=ble_device,
        rssi=-73,
        active=True,
    )


def test_leak_real_data_from_ha():
    """Test parse_advertisement_data for the leak detector."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\\xd6407D1\\x02V\\x90\\x00\\x00\\x00\\x00\\x1e\\x05\\x00\\x00\\x00\\x00"
        },  # no leak, low battery
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"&\\x00V"},
        rssi=-73,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LEAK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "leak": True,
                "tampered": False,
                "battery": 68,
                "low_battery": False,
            },
            "isEncrypted": False,
            "model": "&",
            "modelFriendlyName": "Leak Detector",
            "modelName": SwitchbotModel.LEAK,
            "rawAdvData": b"&\\x00V",
        },
        device=ble_device,
        rssi=-73,
        active=True,
    )


def test_remote_active() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={89: b"\xaa\xbb\xcc\xdd\xee\xff"},
        service_data={"00000d00-0000-1000-8000-00805f9b34fb": b"b V\x00"},
        service_uuids=["cba20d00-224d-11e6-9fb8-0002a5d5c51b"],
        rssi=-95,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 86,
            },
            "isEncrypted": False,
            "model": "b",
            "modelFriendlyName": "Remote",
            "modelName": SwitchbotModel.REMOTE,
            "rawAdvData": b"b V\x00",
        },
        device=ble_device,
        rssi=-95,
        active=True,
    )


def test_remote_passive() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={89: b"\xaa\xbb\xcc\xdd\xee\xff"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.REMOTE)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
            },
            "isEncrypted": False,
            "model": "b",
            "modelFriendlyName": "Remote",
            "modelName": SwitchbotModel.REMOTE,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_parse_advertisement_data_hubmini_matter():
    """Test parse_advertisement_data for the HubMini Matter."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xe6\xa1\xcd\x1f[e\x00\x00\x00\x00\x00\x00\x14\x01\x985\x00"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"%\x00"},
        rssi=-67,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.HUBMINI_MATTER
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.1, "f": 75.38},
                "temperature": 24.1,
            },
            "isEncrypted": False,
            "model": "%",
            "modelFriendlyName": "HubMini Matter",
            "modelName": SwitchbotModel.HUBMINI_MATTER,
            "rawAdvData": b"%\x00",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parse_advertisement_data_roller_shade():
    """Test parse_advertisement_data for roller shade."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeT\x90\x1b,\x08\x9f\x11\x04'\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b",\x00'\x9f\x11\x04"},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.ROLLER_SHADE)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b",\x00'\x9f\x11\x04",
            "data": {
                "battery": 39,
                "calibration": True,
                "deviceChain": 1,
                "inMotion": False,
                "lightLevel": 1,
                "position": 69,
                "sequence_number": 44,
            },
            "isEncrypted": False,
            "model": ",",
            "modelFriendlyName": "Roller Shade",
            "modelName": SwitchbotModel.ROLLER_SHADE,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def test_hubmini_matter_passive() -> None:
    """Test parsing hubmini matter with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xe6\xa1\xcd\x1f[e\x00\x00\x00\x00\x00\x00\x14\x01\x985\x00"
        },
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.HUBMINI_MATTER
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.1, "f": 75.38},
                "temperature": 24.1,
            },
            "isEncrypted": False,
            "model": "%",
            "modelFriendlyName": "HubMini Matter",
            "modelName": SwitchbotModel.HUBMINI_MATTER,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_roller_shade_passive() -> None:
    """Test parsing roller_shade with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeT\x90\x1b,\x08\x9f\x11\x04'\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.ROLLER_SHADE)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "battery": None,
                "calibration": True,
                "deviceChain": 1,
                "inMotion": False,
                "lightLevel": 1,
                "position": 69,
                "sequence_number": 44,
            },
            "isEncrypted": False,
            "model": ",",
            "modelFriendlyName": "Roller Shade",
            "modelName": SwitchbotModel.ROLLER_SHADE,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_circulator_fan_active() -> None:
    """Test parsing circulator fan with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeXY\xa8~LR9"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"~\x00R"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.CIRCULATOR_FAN
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"~\x00R",
            "data": {
                "sequence_number": 126,
                "isOn": False,
                "mode": "baby",
                "nightLight": 3,
                "oscillating": False,
                "battery": 82,
                "speed": 57,
            },
            "isEncrypted": False,
            "model": "~",
            "modelFriendlyName": "Circulator Fan",
            "modelName": SwitchbotModel.CIRCULATOR_FAN,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_circulator_fan_passive() -> None:
    """Test parsing circulator fan with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeXY\xa8~LR9"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.CIRCULATOR_FAN
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 126,
                "isOn": False,
                "mode": "baby",
                "nightLight": 3,
                "oscillating": False,
                "battery": 82,
                "speed": 57,
            },
            "isEncrypted": False,
            "model": "~",
            "modelFriendlyName": "Circulator Fan",
            "modelName": SwitchbotModel.CIRCULATOR_FAN,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_circulator_fan_with_empty_data() -> None:
    """Test parsing circulator fan with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"~\x00R"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.CIRCULATOR_FAN
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"~\x00R",
            "data": {},
            "isEncrypted": False,
            "model": "~",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k20_active() -> None:
    """Test parsing k20 with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfe\x01\xf3\x8f'\x01\x11S\x00\x10d\x0f"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b".\x00d"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.K20_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b".\x00d",
            "data": {
                "sequence_number": 39,
                "soc_version": "1.1.083",
                "step": 0,
                "mqtt_connected": True,
                "battery": 100,
                "work_status": 15,
            },
            "isEncrypted": False,
            "model": ".",
            "modelFriendlyName": "K20 Vacuum",
            "modelName": SwitchbotModel.K20_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k20_passive() -> None:
    """Test parsing k20 with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfe\x01\xf3\x8f'\x01\x11S\x00\x10d\x0f"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.K20_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 39,
                "soc_version": "1.1.083",
                "step": 0,
                "mqtt_connected": True,
                "battery": 100,
                "work_status": 15,
            },
            "isEncrypted": False,
            "model": ".",
            "modelFriendlyName": "K20 Vacuum",
            "modelName": SwitchbotModel.K20_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_k20_with_empty_data() -> None:
    """Test parsing k20 with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b".\x00d"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.K20_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b".\x00d",
            "data": {},
            "isEncrypted": False,
            "model": ".",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k10_pro_active() -> None:
    """Test parsing k10 pro with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeP\x8d\x8d\x02 d"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"(\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.K10_PRO_VACUUM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"(\x00",
            "data": {
                "sequence_number": 2,
                "dusbin_connected": False,
                "dustbin_bound": False,
                "network_connected": True,
                "battery": 100,
                "work_status": 0,
            },
            "isEncrypted": False,
            "model": "(",
            "modelFriendlyName": "K10+ Pro Vacuum",
            "modelName": SwitchbotModel.K10_PRO_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k10_pro_passive() -> None:
    """Test parsing k10 pro with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeP\x8d\x8d\x02 d"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.K10_PRO_VACUUM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 2,
                "dusbin_connected": False,
                "dustbin_bound": False,
                "network_connected": True,
                "battery": 100,
                "work_status": 0,
            },
            "isEncrypted": False,
            "model": "(",
            "modelFriendlyName": "K10+ Pro Vacuum",
            "modelName": SwitchbotModel.K10_PRO_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_k10_pro_with_empty_data() -> None:
    """Test parsing k10 pro with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"(\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.K10_PRO_VACUUM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"(\x00",
            "data": {},
            "isEncrypted": False,
            "model": "(",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k10_active() -> None:
    """Test parsing k10+ with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xca8\x06\xa9_\xf1\x02 d"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"}\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.K10_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"}\x00",
            "data": {
                "sequence_number": 2,
                "dusbin_connected": False,
                "dustbin_bound": False,
                "network_connected": True,
                "battery": 100,
                "work_status": 0,
            },
            "isEncrypted": False,
            "model": "}",
            "modelFriendlyName": "K10+ Vacuum",
            "modelName": SwitchbotModel.K10_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k10_passive() -> None:
    """Test parsing k10+ with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xca8\x06\xa9_\xf1\x02 d"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.K10_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 2,
                "dusbin_connected": False,
                "dustbin_bound": False,
                "network_connected": True,
                "battery": 100,
                "work_status": 0,
            },
            "isEncrypted": False,
            "model": "}",
            "modelFriendlyName": "K10+ Vacuum",
            "modelName": SwitchbotModel.K10_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_k10_with_empty_data() -> None:
    """Test parsing k10+ with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"}\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.K10_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"}\x00",
            "data": {},
            "isEncrypted": False,
            "model": "}",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k10_pro_combo_active() -> None:
    """Test parsing k10+ pro combo with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xb0\xe9\xfe\x01\xf4\x1d\x0b\x01\x01\xb1\x03\x118\x01"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"3\x00\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.K10_PRO_COMBO_VACUUM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"3\x00\x00",
            "data": {
                "sequence_number": 11,
                "soc_version": "1.0.945",
                "step": 1,
                "mqtt_connected": True,
                "battery": 56,
                "work_status": 1,
            },
            "isEncrypted": False,
            "model": "3",
            "modelFriendlyName": "K10+ Pro Combo Vacuum",
            "modelName": SwitchbotModel.K10_PRO_COMBO_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_k10_pro_combo_passive() -> None:
    """Test parsing k10+ pro combo with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xb0\xe9\xfe\x01\xf4\x1d\x0b\x01\x01\xb1\x03\x118\x01"
        },
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.K10_PRO_COMBO_VACUUM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 11,
                "soc_version": "1.0.945",
                "step": 1,
                "mqtt_connected": True,
                "battery": 56,
                "work_status": 1,
            },
            "isEncrypted": False,
            "model": "3",
            "modelFriendlyName": "K10+ Pro Combo Vacuum",
            "modelName": SwitchbotModel.K10_PRO_COMBO_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_k10_pro_combo_with_empty_data() -> None:
    """Test parsing k10+ pro combo with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"3\x00\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.K10_PRO_COMBO_VACUUM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"3\x00\x00",
            "data": {},
            "isEncrypted": False,
            "model": "3",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_s10_active() -> None:
    """Test parsing s10 with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfe\x00\x08|\n\x01\x11\x05\x00\x10M\x02"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"z\x00\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.S10_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"z\x00\x00",
            "data": {
                "sequence_number": 10,
                "soc_version": "1.1.005",
                "step": 0,
                "mqtt_connected": True,
                "battery": 77,
                "work_status": 2,
            },
            "isEncrypted": False,
            "model": "z",
            "modelFriendlyName": "S10 Vacuum",
            "modelName": SwitchbotModel.S10_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_s10_passive() -> None:
    """Test parsing s10 with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfe\x00\x08|\n\x01\x11\x05\x00\x10M\x02"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.S10_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 10,
                "soc_version": "1.1.005",
                "step": 0,
                "mqtt_connected": True,
                "battery": 77,
                "work_status": 2,
            },
            "isEncrypted": False,
            "model": "z",
            "modelFriendlyName": "S10 Vacuum",
            "modelName": SwitchbotModel.S10_VACUUM,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_s10_with_empty_data() -> None:
    """Test parsing s10 with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"z\x00\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.S10_VACUUM)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"z\x00\x00",
            "data": {},
            "isEncrypted": False,
            "model": "z",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xf0\x9e\x9e\x96j\xd6\xa1\x81\x88\xe4\x00\x01\x95\x00\x00",
            b"7\x00\x00\x95-\x00",
            {
                "isOn": True,
                "mode": "level_3",
                "isAqiValid": False,
                "child_lock": False,
                "speed": 100,
                "aqi_level": "excellent",
                "filter element working time": 405,
                "err_code": 0,
                "sequence_number": 161,
            },
            "7",
            "Air Purifier Table",
            SwitchbotModel.AIR_PURIFIER_TABLE,
        ),
        AdvTestCase(
            b'\xcc\x8d\xa2\xa7\x92>\t"\x80\x000\x00\x0f\x00\x00',
            b"*\x00\x00\x15\x04\x00",
            {
                "isOn": False,
                "mode": "auto",
                "isAqiValid": False,
                "child_lock": False,
                "speed": 0,
                "aqi_level": "excellent",
                "filter element working time": 15,
                "err_code": 0,
                "sequence_number": 9,
            },
            "*",
            "Air Purifier",
            SwitchbotModel.AIR_PURIFIER,
        ),
        AdvTestCase(
            b"\xcc\x8d\xa2\xa7\xe4\xa6\x0b\x83\x88d\x00\xea`\x00\x00",
            b"+\x00\x00\x15\x04\x00",
            {
                "isOn": True,
                "mode": "sleep",
                "isAqiValid": False,
                "child_lock": False,
                "speed": 100,
                "aqi_level": "excellent",
                "filter element working time": 60000,
                "err_code": 0,
                "sequence_number": 11,
            },
            "+",
            "Air Purifier",
            SwitchbotModel.AIR_PURIFIER,
        ),
        AdvTestCase(
            b"\xcc\x8d\xa2\xa7\xc1\xae\x9b\x81\x8c\xb2\x00\x01\x94\x00\x00",
            b"8\x00\x00\x95-\x00",
            {
                "isOn": True,
                "mode": "level_2",
                "isAqiValid": True,
                "child_lock": False,
                "speed": 50,
                "aqi_level": "excellent",
                "filter element working time": 404,
                "err_code": 0,
                "sequence_number": 155,
            },
            "8",
            "Air Purifier Table",
            SwitchbotModel.AIR_PURIFIER_TABLE,
        ),
        AdvTestCase(
            b"\xcc\x8d\xa2\xa7\xc1\xae\x9e\xa1\x8c\x800\x01\x95\x00\x00",
            b"8\x00\x00\x95-\x00",
            {
                "isOn": True,
                "mode": "level_1",
                "isAqiValid": True,
                "child_lock": False,
                "speed": 0,
                "aqi_level": "excellent",
                "filter element working time": 405,
                "err_code": 0,
                "sequence_number": 158,
            },
            "8",
            "Air Purifier Table",
            SwitchbotModel.AIR_PURIFIER_TABLE,
        ),
        AdvTestCase(
            b"\xcc\x8d\xa2\xa7\xc1\xae\x9e\x05\x8c\x800\x01\x95\x00\x00",
            b"8\x00\x00\x95-\x00",
            {
                "isOn": False,
                "mode": None,
                "isAqiValid": True,
                "child_lock": False,
                "speed": 0,
                "aqi_level": "excellent",
                "filter element working time": 405,
                "err_code": 0,
                "sequence_number": 158,
            },
            "8",
            "Air Purifier Table",
            SwitchbotModel.AIR_PURIFIER_TABLE,
        ),
    ],
)
def test_air_purifier_active(test_case: AdvTestCase) -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": test_case.service_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": test_case.service_data,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_air_purifier_passive() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xf0\x9e\x9e\x96j\xd6\xa1\x81\x88\xe4\x00\x01\x95\x00\x00"
        },
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.AIR_PURIFIER)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
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
            },
            "isEncrypted": False,
            "model": "+",
            "modelFriendlyName": "Air Purifier",
            "modelName": SwitchbotModel.AIR_PURIFIER,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_air_purifier_with_empty_data() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"+\x00\x00\x15\x04\x00",
        },
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"+\x00\x00\x15\x04\x00",
            "data": {},
            "isEncrypted": False,
            "model": "+",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_hub3_active() -> None:
    """Test parsing hub3 with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfen^)\x00\xffh&\xd6d\x83\x03\x994\x80"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"\x00\x00d\x00\x10\xb9@"
        },
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"\x00\x00d\x00\x10\xb9@",
            "data": {
                "sequence_number": 0,
                "network_state": 2,
                "sensor_inserted": True,
                "lightLevel": 3,
                "illuminance": 90,
                "temperature_alarm": False,
                "humidity_alarm": False,
                "temp": {"c": 25.3, "f": 77.5},
                "temperature": 25.3,
                "humidity": 52,
                "motion_detected": True,
            },
            "isEncrypted": False,
            "model": b"\x00\x10\xb9@",
            "modelFriendlyName": "Hub3",
            "modelName": SwitchbotModel.HUB3,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_hub3_passive() -> None:
    """Test parsing hub3 with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfen^)\x00\xffh&\xd6d\x83\x03\x994\x80"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.HUB3)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 0,
                "network_state": 2,
                "sensor_inserted": True,
                "lightLevel": 3,
                "illuminance": 90,
                "temperature_alarm": False,
                "humidity_alarm": False,
                "temp": {"c": 25.3, "f": 77.5},
                "temperature": 25.3,
                "humidity": 52,
                "motion_detected": True,
            },
            "isEncrypted": False,
            "model": b"\x00\x10\xb9@",
            "modelFriendlyName": "Hub3",
            "modelName": SwitchbotModel.HUB3,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_hub3_with_empty_data() -> None:
    """Test parsing hub3 with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"\x00\x00d\x00\x10\xb9@"
        },
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"\x00\x00d\x00\x10\xb9@",
            "data": {},
            "isEncrypted": False,
            "model": b"\x00\x10\xb9@",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xe9\xd5\x11\xb2kS\x17\x93\x08 ",
            b"-\x80d",
            {
                "sequence_number": 23,
                "battery": 100,
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "update_from_secondary_lock": False,
                "double_lock_mode": False,
                "unlocked_alarm": False,
                "night_latch": False,
            },
            "-",
            "Lock Lite",
            SwitchbotModel.LOCK_LITE,
        ),
        AdvTestCase(
            b"\xee\xf5\xe6\t\x8f\xe8\x11\x97\x08 ",
            b"o\x80d",
            {
                "sequence_number": 17,
                "battery": 100,
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "update_from_secondary_lock": False,
                "door_open": True,
                "double_lock_mode": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "o",
            "Lock",
            SwitchbotModel.LOCK,
        ),
        AdvTestCase(
            b"\xf7a\x07H\xe6\xe8:\x8a\x00d\x00\x00",
            b"$\x80d",
            {
                "sequence_number": 58,
                "battery": 100,
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "update_from_secondary_lock": False,
                "door_open": False,
                "door_open_from_secondary_lock": False,
                "double_lock_mode": False,
                "is_secondary_lock": False,
                "left_battery_compartment_alarm": 0,
                "right_battery_compartment_alarm": 0,
                "low_temperature_alarm": False,
                "manual_unlock_linkage": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "$",
            "Lock Pro",
            SwitchbotModel.LOCK_PRO,
        ),
        AdvTestCase(
            b"\xb0\xe9\xfe\xb6j=%\x8204\x00\x04",
            b"\x00\x804\x00\x10\xa5\xb8",
            {
                "sequence_number": 37,
                "battery": 52,
                "calibration": True,
                "status": LockStatus.LOCKED,
                "update_from_secondary_lock": False,
                "door_open": True,
                "door_open_from_secondary_lock": True,
                "double_lock_mode": False,
                "is_secondary_lock": False,
                "manual_unlock_linkage": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
                "power_alarm": False,
                "battery_status": 4,
            },
            b"\x00\x10\xa5\xb8",
            "Lock Ultra",
            SwitchbotModel.LOCK_ULTRA,
        ),
    ],
)
def test_lock_active(test_case: AdvTestCase) -> None:
    """Test lokc series with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": test_case.service_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": test_case.service_data,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xe9\xd5\x11\xb2kS\x17\x93\x08 ",
            b"-\x80d",
            {
                "sequence_number": 23,
                "battery": None,
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "update_from_secondary_lock": False,
                "double_lock_mode": False,
                "unlocked_alarm": False,
                "night_latch": False,
            },
            "-",
            "Lock Lite",
            SwitchbotModel.LOCK_LITE,
        ),
        AdvTestCase(
            b"\xee\xf5\xe6\t\x8f\xe8\x11\x97\x08 ",
            b"o\x80d",
            {
                "sequence_number": 17,
                "battery": None,
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "update_from_secondary_lock": False,
                "door_open": True,
                "double_lock_mode": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "o",
            "Lock",
            SwitchbotModel.LOCK,
        ),
        AdvTestCase(
            b"\xf7a\x07H\xe6\xe8:\x8a\x00d\x00\x00",
            b"$\x80d",
            {
                "sequence_number": 58,
                "battery": 100,
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "update_from_secondary_lock": False,
                "door_open": False,
                "door_open_from_secondary_lock": False,
                "double_lock_mode": False,
                "is_secondary_lock": False,
                "left_battery_compartment_alarm": 0,
                "right_battery_compartment_alarm": 0,
                "low_temperature_alarm": False,
                "manual_unlock_linkage": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "$",
            "Lock Pro",
            SwitchbotModel.LOCK_PRO,
        ),
        AdvTestCase(
            b"\xb0\xe9\xfe\xb6j=%\x8204\x00\x04",
            b"\x00\x804\x00\x10\xa5\xb8",
            {
                "sequence_number": 37,
                "battery": 52,
                "calibration": True,
                "status": LockStatus.LOCKED,
                "update_from_secondary_lock": False,
                "door_open": True,
                "door_open_from_secondary_lock": True,
                "double_lock_mode": False,
                "is_secondary_lock": False,
                "manual_unlock_linkage": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
                "power_alarm": False,
                "battery_status": 4,
            },
            b"\x00\x10\xa5\xb8",
            "Lock Ultra",
            SwitchbotModel.LOCK_ULTRA,
        ),
    ],
)
def test_lock_passive(test_case: AdvTestCase) -> None:
    """Test lokc series with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, test_case.modelName)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            None,
            b"-\x80d",
            {},
            "-",
            "Lock Lite",
            SwitchbotModel.LOCK_LITE,
        ),
        AdvTestCase(
            None,
            b"o\x80d",
            {},
            "o",
            "Lock",
            SwitchbotModel.LOCK,
        ),
        AdvTestCase(
            None,
            b"$\x80d",
            {},
            "$",
            "Lock Pro",
            SwitchbotModel.LOCK_PRO,
        ),
        AdvTestCase(
            None,
            b"\x00\x804\x00\x10\xa5\xb8",
            {},
            b"\x00\x10\xa5\xb8",
            "Lock Ultra",
            SwitchbotModel.LOCK_ULTRA,
        ),
    ],
)
def test_lock_with_empty_data(test_case: AdvTestCase) -> None:
    """Test lokc series with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": test_case.service_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, test_case.modelName)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": test_case.service_data,
            "data": {},
            "isEncrypted": False,
            "model": test_case.model,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_blind_tilt_active() -> None:
    """Test parsing blind tilt with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xfc(\\6l\x7f\x0b'\x00\xa1\x84"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"x\x00H"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"x\x00H",
            "data": {
                "sequence_number": 11,
                "battery": 72,
                "tilt": 0,
                "inMotion": False,
                "calibration": True,
                "lightLevel": 10,
            },
            "isEncrypted": False,
            "model": "x",
            "modelFriendlyName": "Blind Tilt",
            "modelName": SwitchbotModel.BLIND_TILT,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


def test_blind_tilt_passive() -> None:
    """Test parsing blind tilt with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xfc(\\6l\x7f\x0b'\x00\xa1\x84"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.BLIND_TILT)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "sequence_number": 11,
                "battery": None,
                "tilt": 0,
                "inMotion": False,
                "calibration": True,
                "lightLevel": 10,
            },
            "isEncrypted": False,
            "model": "x",
            "modelFriendlyName": "Blind Tilt",
            "modelName": SwitchbotModel.BLIND_TILT,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_blind_tilt_with_empty_data() -> None:
    """Test parsing blind tilt with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"x\x00H"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"x\x00H",
            "data": {},
            "isEncrypted": False,
            "model": "x",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xa0\xa3\xb3,\x9c\xe68\x86\x88\xb5\x99\x12\x10\x1b\x00\x85]",
            b"#\x00\x00\x15\x1c\x00",
            {
                "seq_number": 56,
                "isOn": True,
                "mode": HumidifierMode(6),
                "over_humidify_protection": True,
                "child_lock": False,
                "tank_removed": False,
                "tilted_alert": False,
                "filter_missing": False,
                "is_meter_binded": True,
                "humidity": 53,
                "temperature": 25.1,
                "temp": {"c": 25.1, "f": 77.18},
                "water_level": "medium",
                "filter_run_time": datetime.timedelta(days=1, seconds=10800),
                "filter_alert": False,
                "target_humidity": 93,
            },
            "#",
            "Evaporative Humidifier",
            SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        ),
        AdvTestCase(
            b"\xa0\xa3\xb3,\x9c\xe6H\x86\x80\x7f\xff\xf2\x10\x1d\x00\x874",
            b"#\x00\x00\x15\x1c\x00",
            {
                "seq_number": 72,
                "isOn": True,
                "mode": HumidifierMode(6),
                "over_humidify_protection": True,
                "child_lock": False,
                "tank_removed": False,
                "tilted_alert": False,
                "filter_missing": False,
                "is_meter_binded": False,
                "humidity": None,
                "temperature": None,
                "temp": {"c": None, "f": None},
                "water_level": "medium",
                "filter_run_time": datetime.timedelta(days=1, seconds=18000),
                "filter_alert": False,
                "target_humidity": 52,
            },
            "#",
            "Evaporative Humidifier",
            SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        ),
        AdvTestCase(
            b"\xa0\xa3\xb3,\x9c\xe6H\x86\x80\xff\xff\xf2\x10\x1d\x00\x874",
            b"#\x00\x00\x15\x1c\x00",
            {
                "seq_number": 72,
                "isOn": True,
                "mode": HumidifierMode(6),
                "over_humidify_protection": True,
                "child_lock": False,
                "tank_removed": False,
                "tilted_alert": False,
                "filter_missing": False,
                "is_meter_binded": True,
                "humidity": None,
                "temperature": None,
                "temp": {"c": None, "f": None},
                "water_level": "medium",
                "filter_run_time": datetime.timedelta(days=1, seconds=18000),
                "filter_alert": False,
                "target_humidity": 52,
            },
            "#",
            "Evaporative Humidifier",
            SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        ),
        AdvTestCase(
            b"\xacg\xb2\xcd\xfa\xbe",
            b"e\x80\x00\xf9\x80Bc\x00",
            {
                "isOn": True,
                "level": 128,
                "switchMode": True,
            },
            "e",
            "Humidifier",
            SwitchbotModel.HUMIDIFIER,
        ),
    ],
)
def test_humidifer_active(test_case: AdvTestCase) -> None:
    """Test humidifier with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": test_case.service_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": test_case.service_data,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xa0\xa3\xb3,\x9c\xe68\x86\x88\xb5\x99\x12\x10\x1b\x00\x85]",
            b"#\x00\x00\x15\x1c\x00",
            {
                "seq_number": 56,
                "isOn": True,
                "mode": HumidifierMode(6),
                "over_humidify_protection": True,
                "child_lock": False,
                "tank_removed": False,
                "tilted_alert": False,
                "filter_missing": False,
                "is_meter_binded": True,
                "humidity": 53,
                "temperature": 25.1,
                "temp": {"c": 25.1, "f": 77.18},
                "water_level": "medium",
                "filter_run_time": datetime.timedelta(days=1, seconds=10800),
                "filter_alert": False,
                "target_humidity": 93,
            },
            "#",
            "Evaporative Humidifier",
            SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        ),
        AdvTestCase(
            b"\xacg\xb2\xcd\xfa\xbe",
            b"e\x80\x00\xf9\x80Bc\x00",
            {
                "isOn": None,
                "level": None,
                "switchMode": True,
            },
            "e",
            "Humidifier",
            SwitchbotModel.HUMIDIFIER,
        ),
    ],
)
def test_humidifer_passive(test_case: AdvTestCase) -> None:
    """Test humidifier with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, test_case.modelName)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


def test_humidifer_with_empty_data() -> None:
    """Test humidifier with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"#\x00\x00\x15\x1c\x00"},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"#\x00\x00\x15\x1c\x00",
            "data": {},
            "isEncrypted": False,
            "model": "#",
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xc0N0\xdd\xb9\xf2\x8a\xc1\x00\x00\x00\x00\x00F\x00\x00",
            b"=\x00\x00\x00",
            {
                1: {
                    "isOn": True,
                    "sequence_number": 138,
                    "switchMode": True,
                },
                2: {
                    "isOn": True,
                    "sequence_number": 138,
                    "switchMode": True,
                },
            },
            "=",
            "Relay Switch 2PM",
            SwitchbotModel.RELAY_SWITCH_2PM,
        ),
        AdvTestCase(
            b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00",
            b";\x00\x00\x00",
            {
                "isOn": True,
                "sequence_number": 71,
                "switchMode": True,
            },
            ";",
            "Relay Switch 1",
            SwitchbotModel.RELAY_SWITCH_1,
        ),
        AdvTestCase(
            b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00",
            b"<\x00\x00\x00",
            {
                "isOn": True,
                "sequence_number": 71,
                "switchMode": True,
            },
            "<",
            "Relay Switch 1PM",
            SwitchbotModel.RELAY_SWITCH_1PM,
        ),
        AdvTestCase(
            b"$X|\x05BN\x0f\x00\x00\x03\x00\x00\x00\x00\x00\x00",
            b">\x00\x00\x00",
            {
                "door_open": True,
                "isOn": False,
                "sequence_number": 15,
                "switchMode": True,
            },
            ">",
            "Garage Door Opener",
            SwitchbotModel.GARAGE_DOOR_OPENER,
        ),
        AdvTestCase(
            b'\xc0N0\xe0U\x9a\x85\x9e"\xd0\x00\x00\x00\x00\x00\x00\x12\x91\x00',
            b"\x00\x00\x00\x00\x10\xd0\xb1",
            {
                "sequence_number": 133,
                "isOn": True,
                "brightness": 30,
                "delay": False,
                "network_state": 2,
                "color_mode": 2,
                "cw": 4753,
            },
            b"\x00\x10\xd0\xb1",
            "Strip Light 3",
            SwitchbotModel.STRIP_LIGHT_3,
        ),
        AdvTestCase(
            b'\xa0\x85\xe3e,\x06P\xaa"\xd4\x00\x00\x00\x00\x00\x00\r\x93\x00',
            b"\x00\x00\x00\x00\x10\xd0\xb0",
            {
                "sequence_number": 80,
                "isOn": True,
                "brightness": 42,
                "delay": False,
                "network_state": 2,
                "color_mode": 2,
                "cw": 3475,
            },
            b"\x00\x10\xd0\xb0",
            "Floor Lamp",
            SwitchbotModel.FLOOR_LAMP,
        ),
        AdvTestCase(
            b"\xef\xfe\xfb\x9d\x10\xfe\n\x01\x18\xf3$",
            b"q\x00",
            {
                "brightness": 1,
                "color_mode": 1,
                "cw": 6387,
                "isOn": False,
                "sequence_number": 10,
            },
            "q",
            "Ceiling Light",
            SwitchbotModel.CEILING_LIGHT,
        ),
        AdvTestCase(
            b'|,g\xc8\x15&jR"l\x00\x00\x00\x00\x00\x00',
            b"r\x00d",
            {
                "brightness": 82,
                "color_mode": 2,
                "delay": False,
                "isOn": False,
                "sequence_number": 106,
                "network_state": 2,
            },
            "r",
            "Light Strip",
            SwitchbotModel.LIGHT_STRIP,
        ),
        AdvTestCase(
            b"@L\xca\xa7_\x12\x02\x81\x12\x00\x00",
            b"u\x00d",
            {
                "brightness": 1,
                "color_mode": 2,
                "delay": False,
                "isOn": True,
                "loop_index": 0,
                "preset": False,
                "sequence_number": 2,
                "speed": 0,
            },
            "u",
            "Color Bulb",
            SwitchbotModel.COLOR_BULB,
        ),
    ],
)
def test_adv_active(test_case: AdvTestCase) -> None:
    """Test with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": test_case.service_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": test_case.service_data,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            b"\xc0N0\xdd\xb9\xf2\x8a\xc1\x00\x00\x00\x00\x00F\x00\x00",
            b"=\x00\x00\x00",
            {
                1: {
                    "isOn": True,
                    "sequence_number": 138,
                    "switchMode": True,
                },
                2: {
                    "isOn": True,
                    "sequence_number": 138,
                    "switchMode": True,
                },
            },
            "=",
            "Relay Switch 2PM",
            SwitchbotModel.RELAY_SWITCH_2PM,
        ),
        AdvTestCase(
            b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00",
            b";\x00\x00\x00",
            {
                "isOn": True,
                "sequence_number": 71,
                "switchMode": True,
            },
            ";",
            "Relay Switch 1",
            SwitchbotModel.RELAY_SWITCH_1,
        ),
        AdvTestCase(
            b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00",
            b"<\x00\x00\x00",
            {
                "isOn": True,
                "sequence_number": 71,
                "switchMode": True,
            },
            "<",
            "Relay Switch 1PM",
            SwitchbotModel.RELAY_SWITCH_1PM,
        ),
        AdvTestCase(
            b"$X|\x05BN\x0f\x00\x00\x03\x00\x00\x00\x00\x00\x00",
            b">\x00\x00\x00",
            {
                "door_open": True,
                "isOn": False,
                "sequence_number": 15,
                "switchMode": True,
            },
            ">",
            "Garage Door Opener",
            SwitchbotModel.GARAGE_DOOR_OPENER,
        ),
        AdvTestCase(
            b'\xc0N0\xe0U\x9a\x85\x9e"\xd0\x00\x00\x00\x00\x00\x00\x12\x91\x00',
            None,
            {
                "sequence_number": 133,
                "isOn": True,
                "brightness": 30,
                "delay": False,
                "network_state": 2,
                "color_mode": 2,
                "cw": 4753,
            },
            b"\x00\x10\xd0\xb1",
            "Strip Light 3",
            SwitchbotModel.STRIP_LIGHT_3,
        ),
        AdvTestCase(
            b'\xa0\x85\xe3e,\x06P\xaa"\xd4\x00\x00\x00\x00\x00\x00\r\x93\x00',
            None,
            {
                "sequence_number": 80,
                "isOn": True,
                "brightness": 42,
                "delay": False,
                "network_state": 2,
                "color_mode": 2,
                "cw": 3475,
            },
            b"\x00\x10\xd0\xb0",
            "Floor Lamp",
            SwitchbotModel.FLOOR_LAMP,
        ),
        AdvTestCase(
            b'|,g\xc8\x15&jR"l\x00\x00\x00\x00\x00\x00',
            None,
            {
                "brightness": 82,
                "color_mode": 2,
                "delay": False,
                "isOn": False,
                "sequence_number": 106,
                "network_state": 2,
            },
            "r",
            "Light Strip",
            SwitchbotModel.LIGHT_STRIP,
        ),
        AdvTestCase(
            b"@L\xca\xa7_\x12\x02\x81\x12\x00\x00",
            None,
            {
                "brightness": 1,
                "color_mode": 2,
                "delay": False,
                "isOn": True,
                "loop_index": 0,
                "preset": False,
                "sequence_number": 2,
                "speed": 0,
            },
            "u",
            "Color Bulb",
            SwitchbotModel.COLOR_BULB,
        ),
    ],
)
def test_adv_passive(test_case: AdvTestCase) -> None:
    """Test with passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: test_case.manufacturer_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data, test_case.modelName)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": test_case.data,
            "isEncrypted": False,
            "model": test_case.model,
            "modelFriendlyName": test_case.modelFriendlyName,
            "modelName": test_case.modelName,
        },
        device=ble_device,
        rssi=-97,
        active=False,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AdvTestCase(
            None,
            b"=\x00\x00\x00",
            {
                1: {
                    "isOn": True,
                    "power": 0.0,
                    "sequence_number": 138,
                    "switchMode": True,
                },
                2: {
                    "isOn": True,
                    "power": 7.0,
                    "sequence_number": 138,
                    "switchMode": True,
                },
            },
            "=",
            "Relay Switch 2PM",
            SwitchbotModel.RELAY_SWITCH_2PM,
        ),
        AdvTestCase(
            None,
            b";\x00\x00\x00",
            {
                "isOn": True,
                "sequence_number": 71,
                "switchMode": True,
            },
            ";",
            "Relay Switch 1",
            SwitchbotModel.RELAY_SWITCH_1,
        ),
        AdvTestCase(
            None,
            b"<\x00\x00\x00",
            {
                "isOn": True,
                "power": 4.9,
                "sequence_number": 71,
                "switchMode": True,
            },
            "<",
            "Relay Switch 1PM",
            SwitchbotModel.RELAY_SWITCH_1PM,
        ),
        AdvTestCase(
            None,
            b">\x00\x00\x00",
            {
                "door_open": True,
                "isOn": False,
                "sequence_number": 15,
                "switchMode": True,
            },
            ">",
            "Garage Door Opener",
            SwitchbotModel.GARAGE_DOOR_OPENER,
        ),
        AdvTestCase(
            None,
            b"\x00\x00\x00\x00\x10\xd0\xb1",
            {},
            b"\x00\x10\xd0\xb1",
            "Strip Light 3",
            SwitchbotModel.STRIP_LIGHT_3,
        ),
        AdvTestCase(
            None,
            b"\x00\x00\x00\x00\x10\xd0\xb0",
            {},
            b"\x00\x10\xd0\xb0",
            "Floor Lamp",
            SwitchbotModel.FLOOR_LAMP,
        ),
        AdvTestCase(
            None,
            b"q\x00",
            {},
            "q",
            "Ceiling Light",
            SwitchbotModel.CEILING_LIGHT,
        ),
        AdvTestCase(
            None,
            b"r\x00d",
            {},
            "r",
            "Light Strip",
            SwitchbotModel.LIGHT_STRIP,
        ),
        AdvTestCase(
            None,
            b"u\x00d",
            {},
            "u",
            "Color Bulb",
            SwitchbotModel.COLOR_BULB,
        ),
    ],
)
def test_adv_with_empty_data(test_case: AdvTestCase) -> None:
    """Test with empty data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: None},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": test_case.service_data},
        rssi=-97,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": test_case.service_data,
            "data": {},
            "isEncrypted": False,
            "model": test_case.model,
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )
