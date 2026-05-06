"""Test keypad device advertisement parsing."""

from switchbot import SwitchbotKeypad
from switchbot.models import SwitchBotAdvertisement

from . import KEYPAD_INFO
from .test_adv_parser import AdvTestCase, generate_ble_device


def make_advertisement_data(
    ble_device, adv_info: AdvTestCase, init_data: dict | None = None
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


def test_keypad_advertisement_battery() -> None:
    """Test that battery is parsed from keypad advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotKeypad(ble_device)
    device.update_from_advertisement(make_advertisement_data(ble_device, KEYPAD_INFO))

    assert device.parsed_data["battery"] == 100


def test_keypad_advertisement_attempt_state() -> None:
    """Test that attempt_state is parsed from keypad advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotKeypad(ble_device)
    device.update_from_advertisement(make_advertisement_data(ble_device, KEYPAD_INFO))

    assert device.parsed_data["attempt_state"] == 143


def test_keypad_advertisement_battery_none() -> None:
    """Test that battery is None when advertisement data is missing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotKeypad(ble_device)
    device.update_from_advertisement(
        make_advertisement_data(ble_device, KEYPAD_INFO, {"battery": None})
    )

    assert device.parsed_data["battery"] is None
