import pytest

from switchbot import SwitchbotModel, parse_advertisement_data

from .test_adv_parser import generate_advertisement_data, generate_ble_device


@pytest.mark.parametrize("network", [0, 0x15, 0x75])
@pytest.mark.parametrize(("status", "is_on"), [(0x01, False), (0x87, True)])
@pytest.mark.parametrize("encrypted", [False, True])
def test_plug_mini_it_advertisement(network, status, is_on, encrypted):
    service = bytes([0x80 if encrypted else 0, 0, 0, 0, 0x12, 0x43, 0xC8, network])
    manufacturer = (
        bytes.fromhex("010203040506")
        + bytes([99, status, 0, 0])
        + bytes.fromhex("04e600000000")
    )
    adv = parse_advertisement_data(
        generate_ble_device("01:02:03:04:05:06", "Plug Mini (IT)"),
        generate_advertisement_data(
            manufacturer_data={2409: manufacturer},
            service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": service},
        ),
    )
    assert adv is not None
    assert adv.data["modelName"] == SwitchbotModel.PLUG_MINI_IT
    assert adv.data["modelFriendlyName"] == "Plug Mini (IT)"
    assert adv.data["isEncrypted"] is encrypted
    assert adv.data["data"] == {
        "switchMode": True,
        "sequence_number": 99,
        "isOn": is_on,
        "power": 1254.0,
    }
