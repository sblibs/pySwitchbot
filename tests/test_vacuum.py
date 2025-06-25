from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement
from switchbot.adv_parser import SUPPORTED_TYPES
from switchbot.devices import vacuum

from .test_adv_parser import generate_ble_device

common_params = [
    (b".\x00d", ".", 2),
    (b"z\x00\x00", ".", 2),
    (b"3\x00\x00", ".", 2),
    (b"(\x00", "(", 1),
    (b"}\x00", "(", 1),
]


def create_device_for_command_testing(
    protocol_version: int, rawAdvData: bytes, model: str
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = vacuum.SwitchbotVacuum(ble_device)
    device.update_from_advertisement(
        make_advertisement_data(ble_device, protocol_version, rawAdvData, model)
    )
    device._send_command = AsyncMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice, protocol_version: int, rawAdvData: bytes, model: str
):
    """Set advertisement data with defaults."""
    if protocol_version == 1:
        return SwitchBotAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            data={
                "rawAdvData": rawAdvData,
                "data": {
                    "sequence_number": 2,
                    "dusbin_connected": False,
                    "dustbin_bound": False,
                    "network_connected": True,
                    "battery": 100,
                    "work_status": 0,
                },
                "isEncrypted": False,
                "model": model,
                "modelFriendlyName": SUPPORTED_TYPES[model]["modelFriendlyName"],
                "modelName": SUPPORTED_TYPES[model]["modelName"],
            },
            device=ble_device,
            rssi=-97,
            active=True,
        )
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": rawAdvData,
            "data": {
                "soc_version": "1.1.083",
                "step": 0,
                "mqtt_connected": True,
                "battery": 100,
                "work_status": 15,
            },
            "isEncrypted": False,
            "model": model,
            "modelFriendlyName": SUPPORTED_TYPES[model]["modelFriendlyName"],
            "modelName": SUPPORTED_TYPES[model]["modelName"],
        },
        device=ble_device,
        rssi=-97,
        active=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    [(b".\x00d", "."), (b"z\x00\x00", "z"), (b"3\x00\x00", "3")],
)
async def test_status_from_proceess_adv(rawAdvData: bytes, model: str) -> None:
    protocol_version = 2
    device = create_device_for_command_testing(protocol_version, rawAdvData, model)
    assert device.get_soc_version() == "1.1.083"
    assert device.get_last_step() == 0
    assert device.get_mqtt_connnect_status() is True
    assert device.get_battery() == 100
    assert device.get_work_status() == 15


@pytest.mark.asyncio
@pytest.mark.parametrize(("rawAdvData", "model"), [(b"(\x00", "("), (b"}\x00", "}")])
async def test_status_from_proceess_adv_k(rawAdvData: bytes, model: str) -> None:
    protocol_version = 1
    device = create_device_for_command_testing(protocol_version, rawAdvData, model)
    assert device.get_dustbin_bound_status() is False
    assert device.get_dustbin_connnected_status() is False
    assert device.get_network_connected_status() is True
    assert device.get_battery() == 100
    assert device.get_work_status() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(("rawAdvData", "model", "protocol_version"), common_params)
async def test_clean_up(rawAdvData, model, protocol_version):
    device = create_device_for_command_testing(protocol_version, rawAdvData, model)
    await device.clean_up(protocol_version)
    device._send_command.assert_awaited_once_with(
        vacuum.COMMAND_CLEAN_UP[protocol_version]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("rawAdvData", "model", "protocol_version"), common_params)
async def test_return_to_dock(rawAdvData, model, protocol_version):
    device = create_device_for_command_testing(protocol_version, rawAdvData, model)
    await device.return_to_dock(protocol_version)
    device._send_command.assert_awaited_once_with(
        vacuum.COMMAND_RETURN_DOCK[protocol_version]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("rawAdvData", "model", "protocol_version"), common_params)
async def test_get_basic_info_returns_none_when_no_data(
    rawAdvData, model, protocol_version
):
    device = create_device_for_command_testing(protocol_version, rawAdvData, model)
    device._get_basic_info = AsyncMock(return_value=None)

    assert await device.get_basic_info() is None
