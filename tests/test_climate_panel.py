"""Tests for the Switchbot Climate Panel device."""

from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices.climate_panel import SwitchbotClimatePanel

from . import CLIMATE_PANEL_INFO, AdvTestCase
from .test_adv_parser import generate_ble_device


def make_advertisement_data(
    ble_device: BLEDevice, adv_info: AdvTestCase
) -> SwitchBotAdvertisement:
    """Build advertisement data for the given test case."""
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": adv_info.service_data,
            "data": adv_info.data,
            "isEncrypted": False,
            "model": adv_info.model,
            "modelFriendlyName": adv_info.modelFriendlyName,
            "modelName": adv_info.modelName,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def create_device_for_command_testing(
    adv_info: AdvTestCase = CLIMATE_PANEL_INFO,
) -> SwitchbotClimatePanel:
    """Create a Climate Panel device populated with advertisement data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotClimatePanel(
        ble_device,
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=adv_info.modelName,
    )
    device.update_from_advertisement(make_advertisement_data(ble_device, adv_info))
    return device


def test_model() -> None:
    """The device reports the Climate Panel model."""
    device = create_device_for_command_testing()
    assert device._model is SwitchbotModel.CLIMATE_PANEL


def test_sensor_values() -> None:
    """Environmental and state getters return parsed advertisement values."""
    device = create_device_for_command_testing()
    assert device.get_current_temperature() == 25.5
    assert device.get_current_humidity() == 45
    assert device.is_on() is False
    assert device.is_motion_detected() is True
    assert device.is_light() is True


def test_keystate_values() -> None:
    """Keystate getters decode the ON/OFF button mode and counter."""
    device = create_device_for_command_testing()
    assert device.get_on_keystate() == 37
    assert device.get_off_keystate() == 98
    assert device.get_on_keystate_mode() == 1
    assert device.get_on_keystate_counter() == 5
    assert device.get_off_keystate_mode() == 3
    assert device.get_off_keystate_counter() == 2
