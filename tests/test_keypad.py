"""Test keypad device advertisement parsing."""

from switchbot import SwitchbotKeypad, SwitchbotModel
from switchbot.adv_parser import parse_advertisement_data

from . import KEYPAD_INFO
from .test_adv_parser import generate_advertisement_data, generate_ble_device


def test_keypad_advertisement_battery() -> None:
    """Test that battery is parsed from keypad advertisement data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: KEYPAD_INFO.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": KEYPAD_INFO.service_data},
        rssi=-80,
    )
    advertisement = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.KEYPAD
    )
    device = SwitchbotKeypad(ble_device)
    device.update_from_advertisement(advertisement)

    assert device.get_battery_percent() == 100


def test_keypad_advertisement_attempt_state() -> None:
    """Test that attempt_state is parsed from keypad advertisement data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: KEYPAD_INFO.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": KEYPAD_INFO.service_data},
        rssi=-80,
    )
    advertisement = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.KEYPAD
    )
    device = SwitchbotKeypad(ble_device)
    device.update_from_advertisement(advertisement)

    assert device.attempt_state == 143


def test_keypad_advertisement_battery_none_when_no_data() -> None:
    """Test that battery is None when advertisement data is missing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": KEYPAD_INFO.service_data},
        rssi=-80,
    )
    advertisement = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.KEYPAD
    )
    device = SwitchbotKeypad(ble_device)
    device.update_from_advertisement(advertisement)

    assert device.get_battery_percent() is None
    assert device.attempt_state is None
