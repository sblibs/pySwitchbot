from unittest.mock import AsyncMock

import pytest

from switchbot import SwitchbotAIMemoryFrame, SwitchbotModel
from switchbot.adv_parser import parse_advertisement_data
from switchbot.adv_parsers.image_frame import process_image_frame
from switchbot.devices.device import SwitchbotOperationError

from .test_adv_parser import generate_advertisement_data, generate_ble_device


@pytest.fixture(params=[SwitchbotAIMemoryFrame])
def device(request):
    frame = request.param(
        generate_ble_device("AA:BB:CC:DD:EE:FF", "Frame"), "ff", "ff" * 16
    )
    frame._send_command = AsyncMock(return_value=b"\x01")
    frame.update = AsyncMock()
    return frame


@pytest.mark.parametrize(
    ("model", "suffix"),
    [
        (SwitchbotModel.AI_MEMORY_FRAME, "1295d0"),
    ],
)
@pytest.mark.parametrize("pairing", [0, 1])
def test_discovery(model, suffix, pairing):
    adv = parse_advertisement_data(
        generate_ble_device("AA:BB:CC:DD:EE:FF", "Frame"),
        generate_advertisement_data(
            service_data={
                "0000fd3d-0000-1000-8000-00805f9b34fb": bytes([0, 0, 54, pairing])
                + bytes.fromhex(suffix)
            },
            manufacturer_data={2409: bytes.fromhex("aabbccddeeff01b634125e")},
        ),
    )
    assert adv.data["modelName"] == model
    assert adv.data["data"] == {
        "sequence_number": 1,
        "battery_charging": True,
        "battery": 54,
        "image_index": 0x1234,
        "display_size": 5,
        "display_mode": 1,
        "last_network_status": 1,
        "orientation": 1,
    }


@pytest.mark.parametrize("data", [None] + [bytes(n) for n in range(11)])
def test_short_advertisements(data):
    assert process_image_frame(None, data) == {}


@pytest.mark.asyncio
async def test_basic_info(device):
    device._get_basic_info = AsyncMock(
        return_value=bytes.fromhex("01b607015c34f1010101")
    )
    assert await device.get_basic_info() == {
        "battery_charging": True,
        "battery": 54,
        "firmware": 0.7,
        "hardware": 1,
        "display_size": 5,
        "display_mode": 1,
        "last_network_status": 1,
        "current_image_index": 0xF134,
        "total_num_of_images": 257,
        "orientation": 1,
    }
    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [None, b"", bytes(9), bytes(10)])
async def test_invalid_basic_info(device, data):
    device._get_basic_info = AsyncMock(return_value=data)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "command"), [("next_image", "570F7A0701"), ("prev_image", "570F7A0700")]
)
@pytest.mark.parametrize(("status", "expected"), [(b"\x01", True), (b"\x09", False)])
async def test_navigation(device, method, command, status, expected):
    device._send_command.return_value = status
    assert await getattr(device, method)() is expected
    device._send_command.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_paginated_bitmap(device):
    device._send_command.side_effect = [b"\x01\x02\x00\x81\x01", b"\x01\x02\x01\x02"]
    assert await device._get_image_indexes() == [1, 8, 9, 18]
    assert [call.args[0] for call in device._send_command.await_args_list] == [
        "570F7B0700",
        "570F7B0701",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "responses",
    [
        [None],
        [b"\x01"],
        [b"\x09\x01\x00\x01"],
        [b"\x01\x00\x00\x01"],
        [b"\x01\x01\x01\x01"],
        [b"\x01\x02\x00\x01", b"\x01\x03\x01\x01"],
        [b"\x01\x02\x00\x01", b"\x01\x02\x00\x01"],
        [b"\x01\x01\x00" + bytes(2561)],
    ],
)
async def test_invalid_bitmap(device, responses):
    device._send_command.side_effect = responses
    with pytest.raises(SwitchbotOperationError, match="Invalid image bitmap"):
        await device._get_image_indexes()


@pytest.mark.asyncio
async def test_random_sparse_image(device):
    device.get_basic_info = AsyncMock(return_value={"current_image_index": 1})
    device._send_command.side_effect = [
        b"\x01\x01\x00\x01" + bytes(31) + b"\x01",
        b"\x01",
    ]
    assert await device.random_image()
    device._send_command.assert_awaited_with("570F7A020101")


@pytest.mark.asyncio
@pytest.mark.parametrize("bitmap", [b"\x00", b"\x01"])
async def test_random_without_alternative(device, bitmap):
    device.get_basic_info = AsyncMock(return_value={"current_image_index": 1})
    device._send_command.return_value = b"\x01\x01\x00" + bitmap
    with pytest.raises(RuntimeError, match="No images"):
        await device.random_image()


@pytest.mark.asyncio
async def test_random_without_info(device):
    device.get_basic_info = AsyncMock(return_value=None)
    with pytest.raises(SwitchbotOperationError, match="Failed to retrieve"):
        await device.random_image()
    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_image(device):
    device._send_command.side_effect = [
        b"\x01\x01\x00" + bytes(2559) + b"\x80",
        b"\x01",
    ]
    assert await device.set_image(0)
    device._send_command.assert_awaited_with("570F7A020050")


@pytest.mark.asyncio
@pytest.mark.parametrize("index", [-1, 1])
async def test_set_out_of_range(device, index):
    device._send_command.return_value = b"\x01\x01\x00\x01"
    with pytest.raises(ValueError, match="out of range"):
        await device.set_image(index)
