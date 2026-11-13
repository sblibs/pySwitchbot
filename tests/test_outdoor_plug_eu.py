from unittest.mock import AsyncMock

import pytest

from switchbot import (
    SwitchBotAdvertisement,
    SwitchbotModel,
    SwitchbotOutdoorPlug,
    parse_advertisement_data,
)
from switchbot.adv_parsers.plug import process_outdoor_plug
from switchbot.devices.device import API_MODEL_TO_ENUM

from .test_adv_parser import generate_advertisement_data, generate_ble_device


@pytest.mark.parametrize("network", [0, 0x15, 0x75])
@pytest.mark.parametrize(("status", "is_on"), [(0x01, False), (0x87, True)])
@pytest.mark.parametrize("encrypted", [False, True])
def test_outdoor_plug_eu_advertisement(network, status, is_on, encrypted):
    service = bytes([0x80 if encrypted else 0, 0, 0, 0, 0x12, 0x18, 0xD0, network])
    manufacturer = (
        bytes.fromhex("010203040506")
        + bytes([99, status, 0, 0])
        + bytes.fromhex("04e6007b0000")
    )
    adv = parse_advertisement_data(
        generate_ble_device("01:02:03:04:05:06", "Outdoor Plug (EU)"),
        generate_advertisement_data(
            manufacturer_data={2409: manufacturer},
            service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": service},
        ),
    )
    assert adv is not None
    assert adv.data["modelName"] == SwitchbotModel.OUTDOOR_PLUG_EU
    assert adv.data["modelFriendlyName"] == "Outdoor Plug (EU)"
    assert adv.data["isEncrypted"] is encrypted
    assert adv.data["data"] == {
        "switchMode": True,
        "sequence_number": 99,
        "isOn": is_on,
        "power": 1254.0,
        "power_production": 123.0,
    }


def create_device():
    return SwitchbotOutdoorPlug(
        generate_ble_device("01:02:03:04:05:06", "Outdoor Plug"),
        "ff",
        "ffffffffffffffffffffffffffffffff",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("is_on", [False, True])
async def test_bidirectional_metering(is_on):
    device = create_device()
    device.get_current_time_and_start_time = lambda: ("00000010", "00000000")
    common = bytes([1, 99, 0x81 if is_on else 1]) + bytes(13) + bytes([3])
    consumed = bytes.fromhex("0100ea60003a98003c08fc03e808fc")
    produced = bytes.fromhex("0100bb80007530001e08fc07d011f8")
    device._get_basic_info = AsyncMock(side_effect=[common, consumed, produced])
    info = await device.get_basic_info()
    assert info["isOn"] is is_on
    assert info["energy"] == 1.0
    assert info["energy_production"] == 0.8
    assert info["power"] == (230.0 if is_on else 0)
    assert info["power_production"] == (460.0 if is_on else 0)
    assert info["current"] == (1.0 if is_on else 0)
    assert info["current_production"] == (2.0 if is_on else 0)
    assert info["voltage"] == (230 if is_on else 0)
    assert device._get_basic_info.call_args_list[1].args == (
        "570f7106000000001000000000",
    )
    assert device._get_basic_info.call_args_list[2].args == (
        "570f7106010000001000000000",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [None, b"", b"\x01", bytes(14)])
async def test_short_production_response(reply):
    device = create_device()
    common = bytes([1, 99, 0x81]) + bytes(13) + bytes([3])
    device._get_basic_info = AsyncMock(side_effect=[common, bytes(15), reply])
    assert await device.get_basic_info() is None


@pytest.mark.parametrize("manufacturer", [None, b"", bytes(13)])
def test_short_advertisement(manufacturer):

    assert process_outdoor_plug(None, manufacturer) == {}


@pytest.mark.asyncio
async def test_advertisement_preserves_energy_and_refreshes_power():
    device = create_device()
    device.update = AsyncMock()

    def advertisement(sequence, power, production):
        return SwitchBotAdvertisement(
            address="01:02:03:04:05:06",
            data={
                "data": {
                    "sequence_number": sequence,
                    "isOn": True,
                    "power": power,
                    "power_production": production,
                }
            },
            device=device._device,
            rssi=-40,
            active=True,
        )

    device.update_from_advertisement(advertisement(1, 20, 30))
    device.data["data"].update(
        {"energy": 1.2, "energy_production": 3.4, "current_production": 0.5}
    )
    device.update_from_advertisement(advertisement(2, 40, 50))
    assert device.parsed_data["energy"] == 1.2
    assert device.parsed_data["energy_production"] == 3.4
    assert device.parsed_data["current_production"] == 0.5
    assert device.parsed_data["power"] == 40
    assert device.parsed_data["power_production"] == 50


def test_cloud_model_mapping():
    assert API_MODEL_TO_ENUM["W1186000"] is SwitchbotModel.OUTDOOR_PLUG_EU
