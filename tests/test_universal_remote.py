from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot.devices.universal_remote import SwitchbotUniversalRemote


def create_device() -> SwitchbotUniversalRemote:
    """Create a Universal Remote device for command testing."""
    ble_device = BLEDevice(
        address="aa:bb:cc:dd:ee:ff", name="any", details={"rssi": -80}
    )
    device = SwitchbotUniversalRemote(ble_device)
    device._send_command = AsyncMock()
    return device


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            b"\x01\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            {"battery": 80, "charging": False},
        ),
        (
            b"\x01\x37\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            {"battery": 55, "charging": True},
        ),
    ],
)
async def test_get_basic_info(response: bytes, expected: dict[str, int | bool]) -> None:
    """Test get_basic_info parses battery and charging state."""
    device = create_device()
    device._get_basic_info = AsyncMock(return_value=response)

    info = await device.get_basic_info()

    assert info == expected


@pytest.mark.asyncio
async def test_get_basic_info_returns_none_on_empty_response() -> None:
    """get_basic_info returns None when the device gives no data."""
    device = create_device()
    device._get_basic_info = AsyncMock(return_value=None)

    assert await device.get_basic_info() is None
