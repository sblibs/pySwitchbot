from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement
from switchbot.devices.climate_panel import SwitchbotClimatePanel

from . import CLIMATE_PANEL_INFO
from .test_adv_parser import AdvTestCase, generate_ble_device


def create_device_for_command_testing(
    adv_info: AdvTestCase,
    init_data: dict | None = None,
) -> SwitchbotClimatePanel:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotClimatePanel(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=adv_info.modelName
    )
    device.update_from_advertisement(
        make_advertisement_data(ble_device, adv_info, init_data)
    )
    return device


def make_advertisement_data(
    ble_device: BLEDevice, adv_info: AdvTestCase, init_data: dict | None = None
) -> SwitchBotAdvertisement:
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


def test_climate_panel_adv_values() -> None:
    device = create_device_for_command_testing(CLIMATE_PANEL_INFO)

    assert device.get_current_temperature() == 25.5
    assert device.get_current_humidity() == 45
    assert device.get_battery_percent() == 20
    assert device.is_on() is False
    assert device.is_motion_detected() is True
    assert device.is_light() is True
    assert device.get_on_button_mode() == 1
    assert device.get_on_button_counter() == 5
    assert device.get_off_button_mode() == 0
    assert device.get_off_button_counter() == 0
