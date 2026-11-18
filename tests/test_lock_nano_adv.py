import pytest

from switchbot import SwitchbotModel, parse_advertisement_data
from switchbot.adv_parsers.lock import process_lock_nano
from switchbot.const.lock import LockStatus
from switchbot.devices.lock import SwitchbotLock

from .test_adv_parser import generate_advertisement_data, generate_ble_device


@pytest.mark.parametrize("pairing", [0, 1])
def test_nano_discovery(pairing):
    service_data = bytes([0, 0x80, 95, pairing, 0x12, 0x24, 0x88])
    manufacturer_data = bytes.fromhex("b0e9fe112233 2a 88 fe df 73")
    advertisement = generate_advertisement_data(
        manufacturer_data={2409: manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": service_data},
        rssi=-60,
    )
    result = parse_advertisement_data(
        generate_ble_device("aa:bb:cc:dd:ee:ff", "Lock Nano"), advertisement
    )
    assert result.data["modelName"] == SwitchbotModel.LOCK_NANO
    assert result.data["data"] == {
        "sequence_number": 42,
        "calibration": True,
        "status": LockStatus.UNLOCKED,
        "auto_lock_paused": True,
        "night_latch": True,
        "battery": 95,
        "charging_status": 1,
        "battery_charging": True,
        "unlocked_alarm": True,
        "low_temperature_alarm": True,
        "power_alarm": True,
        "battery_status": 1,
        "charging_fault": True,
    }


@pytest.mark.parametrize(
    ("flags", "battery", "expected"),
    [
        (0, 95, 0),
        (0, 223, 1),
        (1, 95, 2),
        (1, 223, 3),
    ],
)
def test_nano_charging_status(flags, battery, expected):
    manufacturer_data = bytes.fromhex("b0e9fe112233 01 80") + bytes([flags, battery, 0])
    result = process_lock_nano(None, manufacturer_data)
    assert result["charging_status"] == expected
    assert result["battery_charging"] == (expected == 1)
    assert result["battery"] == 95


@pytest.mark.parametrize("manufacturer_data", [None, b"", bytes(6), bytes(10)])
def test_nano_truncated_advertisement(manufacturer_data):
    assert process_lock_nano(None, manufacturer_data) == {}


@pytest.mark.parametrize(("alarm_byte", "expected"), [(0, 0), (2, 1), (4, 2)])
def test_nano_battery_status(alarm_byte, expected):
    result = process_lock_nano(None, bytes(10) + bytes([alarm_byte]))
    assert result["battery_status"] == expected
    assert not result["charging_fault"]


def test_nano_connected_layout():
    assert SwitchbotLock._parse_lock_data(
        bytes.fromhex("88 10 64 00 00 80"), SwitchbotModel.LOCK_NANO
    ) == {
        "calibration": True,
        "status": LockStatus.UNLOCKED,
        "unlocked_alarm": False,
        "auto_lock_paused": False,
    }
