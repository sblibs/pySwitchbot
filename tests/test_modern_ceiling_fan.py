from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import pytest_asyncio

from switchbot import (
    SwitchbotModel,
    SwitchbotModernCeilingFan,
    fetch_cloud_devices_by_token,
    parse_advertisement_data,
)
from switchbot.adv_parser import _MODEL_TO_MAC_CACHE
from switchbot.adv_parsers.modern_ceiling_fan import process_modern_ceiling_fan
from switchbot.devices.device import SwitchbotBaseDevice

from .test_adv_parser import generate_advertisement_data, generate_ble_device

MFR = bytes.fromhex("aabbccddeeff01d0962ab20fa0c6020000")


@pytest_asyncio.fixture
async def device():
    ble = generate_ble_device("AA:BB:CC:DD:EE:FF", "Modern Ceiling Fan")
    frame = SwitchbotModernCeilingFan(ble, "ff", "ff" * 16)
    frame.update = AsyncMock()
    adv = parse_advertisement_data(
        ble,
        generate_advertisement_data(
            manufacturer_data={2409: MFR},
            service_data={
                "0000fd3d-0000-1000-8000-00805f9b34fb": bytes.fromhex("00005000105798")
            },
        ),
    )
    frame.update_from_advertisement(adv)
    frame._send_command = AsyncMock(return_value=b"\x01")
    frame.update = AsyncMock()
    return frame


@pytest.mark.parametrize("pairing", [0, 1])
def test_discovery(pairing):
    adv = parse_advertisement_data(
        generate_ble_device("AA:BB:CC:DD:EE:FF"),
        generate_advertisement_data(
            manufacturer_data={2409: MFR},
            service_data={
                "0000fd3d-0000-1000-8000-00805f9b34fb": bytes(
                    [0, 0, 80, pairing, 0x10, 0x57, 0x98]
                )
            },
        ),
    )
    assert adv.data["modelName"] == SwitchbotModel.MODERN_CEILING_FAN
    assert adv.data["data"] == {
        "sequence_number": 1,
        "isOn": True,
        "mode": "normal",
        "battery": 80,
        "charging": True,
        "speed": 42,
        "night_light_is_on": True,
        "night_light_level": 1,
        "oscillating": True,
        "oscillating_horizontal": True,
        "oscillating_vertical": False,
        "main_light_is_on": True,
        "main_light_brightness": 50,
        "main_light_color_temp": 4000,
        "color_light_is_on": True,
        "color_light_brightness": 70,
        "color_light_mode": 2,
    }


@pytest.mark.parametrize("data", [None] + [bytes(n) for n in range(17)])
def test_short_advertisement(data):
    assert process_modern_ceiling_fan(None, data) == {}


@pytest.mark.asyncio
async def test_state(device):
    assert device._model == SwitchbotModel.MODERN_CEILING_FAN
    assert device.main_light_is_on is True
    assert device.main_light_brightness == 50
    assert device.main_light_color_temp == 4000
    assert device.color_light_is_on is True
    assert device.color_light_brightness == 70
    assert device.color_light_rgb is None
    assert device.fan_modes == ["normal", "natural", "sleep", "hurricane", "reverse"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args", "commands"),
    [
        ("turn_on", (), ["570f41112901"]),
        ("turn_off", (), ["570f41112900"]),
        ("set_preset_mode", ("reverse",), ["570f4111290106"]),
        ("set_percentage", (42,), ["570f41112901012A"]),
        ("set_oscillation", (True,), ["570f4102010101"]),
        ("set_horizontal_oscillation", (False,), ["570f41020102ff"]),
        ("set_vertical_oscillation", (True,), ["570f410201ff01"]),
        ("set_main_light", (True,), ["570f4911290181"]),
        ("set_main_light", (False,), ["570f4911290182"]),
        ("set_main_light", (True, 50), ["570f4911290181", "570f4911290932"]),
        ("set_main_light", (True, None, 4000), ["570f4911290181", "570f491129100FA0"]),
        ("set_main_light", (True, 50, 4000), ["570f4911290181", "570f49112911320FA0"]),
        ("set_color_light", (True,), ["570f4911290184"]),
        ("set_color_light", (False,), ["570f4911290188"]),
        ("set_color_light", (True, 50), ["570f4911290184", "570f4911291432"]),
        (
            "set_color_light",
            (True, 50, (10, 20, 30)),
            ["570f4911290184", "570f49112912320a141e00ff"],
        ),
        (
            "set_color_light",
            (True, None, (10, 20, 30)),
            ["570f4911290184", "570f49112912460a141e00ff"],
        ),
    ],
)
async def test_commands(device, method, args, commands):
    assert await getattr(device, method)(*args)
    assert [call.args[0] for call in device._send_command.await_args_list] == commands


@pytest.mark.asyncio
async def test_reverse_speed(device):
    packet = bytearray(MFR)
    packet[8] = 0xE0
    assert process_modern_ceiling_fan(None, bytes(packet))["mode"] == "reverse"
    device._update_parsed_data({"mode": "reverse"})
    await device.set_percentage(25)
    device._send_command.assert_awaited_once_with("570f411129010619")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("set_main_light", (True, 0)),
        ("set_main_light", (True, 50, 6501)),
        ("set_color_light", (True, 101)),
        ("set_color_light", (True, 50, (256, 0, 0))),
    ],
)
async def test_invalid_values(device, method, args):
    with pytest.raises(ValueError, match="must be between"):
        await getattr(device, method)(*args)
    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["set_main_light", "set_color_light"])
async def test_power_failure(device, method):
    device._send_command.return_value = b"\x09"
    assert await getattr(device, method)(True, 50) is False
    assert device._send_command.await_count == 1


@pytest.mark.asyncio
async def test_polling(device):
    device._get_basic_info = AsyncMock(return_value=bytes.fromhex("01001c"))
    device._send_command.return_value = bytes.fromhex(
        "010700320fa04628507802805a005a012a"
    )
    assert await device.get_basic_info() == {
        "firmware": 2.8,
        "color_light_rgb": (40, 80, 120),
    }
    assert device.main_light_brightness == 50
    assert device.is_on() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [None, b"", bytes(16), bytes(17)])
async def test_invalid_status(device, data):
    device._get_basic_info = AsyncMock(return_value=bytes.fromhex("01001c"))
    device._send_command.return_value = data
    assert await device.get_basic_info() == {"firmware": 2.8}


@pytest.mark.asyncio
async def test_cloud_mapping():
    with (
        patch.dict(_MODEL_TO_MAC_CACHE, {}, clear=True),
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value={"botRegion": "us"},
        ),
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            return_value={
                "Items": [
                    {
                        "device_mac": "aabbccddeeff",
                        "device_detail": {"device_type": "W1071000"},
                    }
                ]
            },
        ),
    ):
        assert await fetch_cloud_devices_by_token(
            MagicMock(spec=aiohttp.ClientSession), "token"
        ) == {"AA:BB:CC:DD:EE:FF": SwitchbotModel.MODERN_CEILING_FAN}
        assert (
            _MODEL_TO_MAC_CACHE["AA:BB:CC:DD:EE:FF"]
            == SwitchbotModel.MODERN_CEILING_FAN
        )


@pytest.mark.parametrize(
    ("fan_on", "white_on", "color_on"),
    [
        (False, False, False),
        (True, False, True),
        (False, True, False),
        (True, True, True),
    ],
)
def test_independent_power(fan_on, white_on, color_on):
    packet = bytearray(MFR)
    packet[8] = (packet[8] & 0x7F) | (0x80 if fan_on else 0)
    packet[10] = (packet[10] & 0x7F) | (0x80 if white_on else 0)
    packet[13] = (packet[13] & 0x7F) | (0x80 if color_on else 0)
    state = process_modern_ceiling_fan(None, bytes(packet))
    assert state["isOn"] is fan_on
    assert state["main_light_is_on"] is white_on
    assert state["color_light_is_on"] is color_on


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (0, None),
        (1, "normal"),
        (2, "natural"),
        (3, "sleep"),
        (4, "hurricane"),
        (5, None),
        (6, "reverse"),
        (7, None),
    ],
)
def test_modes(mode, expected):
    packet = bytearray(MFR)
    packet[8] = (packet[8] & 0x8F) | (mode << 4)
    assert process_modern_ceiling_fan(None, bytes(packet))["mode"] == expected
