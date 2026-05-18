r"""
Regression tests: device-level get_basic_info must not crash on short responses.

Each device class's `get_basic_info()` accesses fixed byte offsets in the response
payload. A truncated reply (BLE proxy strips bytes, device firmware error, etc.)
must return None instead of raising IndexError.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchbotModel
from switchbot.devices import (
    air_purifier,
    art_frame,
    blind_tilt,
    bot,
    bulb,
    ceiling_light,
    curtain,
    evaporative_humidifier,
    fan,
    keypad_vision,
    light_strip,
    roller_shade,
    smart_thermostat_radiator,
    vacuum,
)

from .test_adv_parser import generate_ble_device


def _ble() -> BLEDevice:
    return generate_ble_device("aa:bb:cc:dd:ee:ff", "any")


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02", b"\x01\x02\x03"])
async def test_bot_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotBot.get_basic_info accesses _data[10] — short reply must return None."""
    device = bot.Switchbot(_ble())
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_short",
    [b"", b"\x01", b"\x01" * 10],
)
async def test_bulb_get_basic_info_short_returns_none(data_short: bytes) -> None:
    """SwitchbotBulb.get_basic_info accesses _data[10] — short reply must return None."""
    device = bulb.SwitchbotBulb(_ble())
    # _get_multi_commands_results returns (version_info, data); fake both short.
    device._get_multi_commands_results = AsyncMock(
        return_value=(b"\x01\x02\x03", data_short)
    )
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_bulb_get_basic_info_short_version_returns_none() -> None:
    """SwitchbotBulb.get_basic_info needs version_info[2] — short reply must return None."""
    device = bulb.SwitchbotBulb(_ble())
    device._get_multi_commands_results = AsyncMock(return_value=(b"\x01", b"\x00" * 16))
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_ceiling_light_get_basic_info_short_data_returns_none() -> None:
    """SwitchbotCeilingLight.get_basic_info needs _data >= 5."""
    device = ceiling_light.SwitchbotCeilingLight(_ble())
    device._get_multi_commands_results = AsyncMock(
        return_value=(b"\x01\x02\x03", b"\x01\x02")
    )
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_ceiling_light_get_basic_info_short_version_returns_none() -> None:
    """SwitchbotCeilingLight.get_basic_info needs version_info >= 3."""
    device = ceiling_light.SwitchbotCeilingLight(_ble())
    device._get_multi_commands_results = AsyncMock(return_value=(b"\x01", b"\x00" * 8))
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02", b"\x01" * 9])
async def test_fan_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotFan.get_basic_info accesses _data[9] — short reply must return None."""
    ble = _ble()
    # Use a concrete subclass with a _mode_enum defined.
    device = fan.SwitchbotFan(ble)
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_fan_get_basic_info_short_firmware_returns_none() -> None:
    """SwitchbotFan.get_basic_info accesses _data1[2] — short firmware reply returns None."""
    device = fan.SwitchbotFan(_ble())
    # First call returns a sufficiently-long data buffer; second (firmware) is short.
    device._send_command = AsyncMock(side_effect=[b"\x01" + b"\x80" * 10, b"\x01\x02"])
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02", b"\x01" * 14])
async def test_keypad_vision_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotKeypadVision.get_basic_info accesses _data[14] — short reply returns None."""
    device = keypad_vision.SwitchbotKeypadVision(
        _ble(),
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.KEYPAD_VISION,
    )
    device._get_basic_info = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "short"),
    [
        (SwitchbotModel.KEYPAD_VISION, b"\x01\x02"),
        (SwitchbotModel.KEYPAD_VISION, b"\x01" * 5),
        (SwitchbotModel.KEYPAD_VISION_PRO, b"\x01" * 7),
    ],
)
async def test_keypad_vision_get_password_count_short_returns_none(
    model: SwitchbotModel, short: bytes
) -> None:
    device = keypad_vision.SwitchbotKeypadVision(
        _ble(), "ff", "ffffffffffffffffffffffffffffffff", model=model
    )
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_password_count() is None


@pytest.mark.asyncio
async def test_air_purifier_get_basic_info_short_data_returns_none() -> None:
    """SwitchbotAirPurifier.get_basic_info needs _data >= 16."""
    device = air_purifier.SwitchbotAirPurifier(
        _ble(),
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.AIR_PURIFIER_TABLE_US,
    )
    device._get_basic_info_by_multi_commands = AsyncMock(
        return_value=[b"\x01" * 10, b"\x01" * 6, b"\x01" * 2]
    )
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_air_purifier_get_basic_info_short_led_returns_none() -> None:
    """SwitchbotAirPurifier.get_basic_info needs led_settings >= 6."""
    device = air_purifier.SwitchbotAirPurifier(
        _ble(),
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.AIR_PURIFIER_TABLE_US,
    )
    device._get_basic_info_by_multi_commands = AsyncMock(
        return_value=[b"\x01" * 16, b"\x01" * 3, b"\x01" * 2]
    )
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02", b"\x01" * 7])
async def test_blind_tilt_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotBlindTilt.get_basic_info accesses _data[7] — short reply returns None."""
    device = blind_tilt.SwitchbotBlindTilt(_ble())
    device._get_basic_info = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_blind_tilt_get_extended_info_summary_short_returns_none() -> None:
    """SwitchbotBlindTilt.get_extended_info_summary accesses _data[1] — short reply returns None."""
    device = blind_tilt.SwitchbotBlindTilt(_ble())
    device._send_command = AsyncMock(return_value=b"\x01")
    assert await device.get_extended_info_summary() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02", b"\x01" * 7])
async def test_curtain_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotCurtain.get_basic_info accesses _data[7] — short reply returns None."""
    device = curtain.SwitchbotCurtain(_ble())
    device._get_basic_info = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_curtain_get_extended_info_summary_short_returns_none() -> None:
    """SwitchbotCurtain.get_extended_info_summary accesses _data[2] — short reply returns None."""
    device = curtain.SwitchbotCurtain(_ble())
    device._send_command = AsyncMock(return_value=b"\x01\x02")
    assert await device.get_extended_info_summary() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02", b"\x01\x02\x03"])
async def test_curtain_get_extended_info_adv_short_returns_none(short: bytes) -> None:
    """get_extended_info_adv accesses _data[3] on device0 — short reply returns None."""
    device = curtain.SwitchbotCurtain(_ble())
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_extended_info_adv() is None


@pytest.mark.asyncio
async def test_curtain_get_extended_info_adv_single_device_short_skips_device1() -> (
    None
):
    """A 4-byte reply parses device0 only; the device1 block (needs _data[6]) is skipped."""
    device = curtain.SwitchbotCurtain(_ble())
    # _data[0]=hdr, [1]=battery, [2]=firmware*10, [3]=stateOfCharge index (0..5)
    device._send_command = AsyncMock(return_value=b"\x00\x55\x32\x01")
    result = await device.get_extended_info_adv()
    assert result is not None
    assert "device0" in result
    assert result["device0"] == {
        "battery": 0x55,
        "firmware": 5.0,
        "stateOfCharge": "charging_by_adapter",
    }
    assert "device1" not in result


@pytest.mark.asyncio
async def test_curtain_get_extended_info_adv_truncated_device1_does_not_crash() -> None:
    """A reply with _data[4] set but <7 bytes total must not IndexError on _data[5]/_data[6]."""
    device = curtain.SwitchbotCurtain(_ble())
    # _data[4]=0x55 would normally trigger the device1 branch; len=6 is one short of _data[6].
    device._send_command = AsyncMock(return_value=b"\x00\x55\x32\x01\x55\x32")
    result = await device.get_extended_info_adv()
    assert result is not None
    assert "device1" not in result


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01" * 5, b"\x01" * 10])
async def test_evaporative_humidifier_get_basic_info_short_returns_none(
    short: bytes,
) -> None:
    """SwitchbotEvaporativeHumidifier.get_basic_info accesses _data[10]."""
    device = evaporative_humidifier.SwitchbotEvaporativeHumidifier(
        _ble(), "ff", "ffffffffffffffffffffffffffffffff"
    )
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_light_strip_get_basic_info_short_data_returns_none() -> None:
    """SwitchbotLightStrip.get_basic_info needs _data >= 11."""
    device = light_strip.SwitchbotLightStrip(_ble())
    device._get_multi_commands_results = AsyncMock(
        return_value=(b"\x01\x02\x03", b"\x01" * 5)
    )
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_candle_warmer_lamp_get_basic_info_short_data_returns_none() -> None:
    """SwitchbotCandleWarmerLamp.get_basic_info needs _data >= 3 and version_info >= 3."""
    device = light_strip.SwitchbotCandleWarmerLamp(
        _ble(), "ff", "ffffffffffffffffffffffffffffffff"
    )
    device._get_multi_commands_results = AsyncMock(
        return_value=(b"\x01\x02\x03", b"\x01\x02")
    )
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01" * 5, b"\x01" * 6])
async def test_roller_shade_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotRollerShade.get_basic_info accesses _data[6] — short reply returns None."""
    device = roller_shade.SwitchbotRollerShade(_ble())
    device._get_basic_info = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01" * 10, b"\x01" * 14])
async def test_smart_thermostat_radiator_get_basic_info_short_returns_none(
    short: bytes,
) -> None:
    """SwitchbotSmartThermostatRadiator.get_basic_info accesses _data[14]."""
    device = smart_thermostat_radiator.SwitchbotSmartThermostatRadiator(
        _ble(),
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.SMART_THERMOSTAT_RADIATOR,
    )
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01\x02"])
async def test_vacuum_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotVacuum.get_basic_info accesses _data[2] — short reply returns None."""
    device = vacuum.SwitchbotVacuum(_ble())
    device._send_command = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [b"\x01", b"\x01" * 5, b"\x01" * 6])
async def test_art_frame_get_basic_info_short_returns_none(short: bytes) -> None:
    """SwitchbotArtFrame.get_basic_info accesses _data[6] (total_num_of_images)."""
    device = art_frame.SwitchbotArtFrame(
        _ble(),
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.ART_FRAME,
    )
    device._get_basic_info = AsyncMock(return_value=short)
    assert await device.get_basic_info() is None


@pytest.mark.asyncio
async def test_art_frame_get_basic_info_truncated_images_returns_none() -> None:
    """ArtFrame: total_num_of_images = 5 but only 1 image-index byte present."""
    device = art_frame.SwitchbotArtFrame(
        _ble(),
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.ART_FRAME,
    )
    # _data[6] = 5 (claims 5 images) but buffer ends at byte 7 (only 1 image byte).
    device._get_basic_info = AsyncMock(return_value=b"\x01\x02\x03\x04\x05\x06\x05\xaa")
    assert await device.get_basic_info() is None
