from unittest.mock import AsyncMock, Mock, patch

import pytest
from bleak.exc import BleakError

from switchbot import CurtainChargingState
from switchbot.devices.base_cover import COVER_EXT_ADV_KEY, COVER_EXT_SUM_KEY
from switchbot.devices.curtain import CURTAIN_EXT_CHAIN_INFO_KEY, SwitchbotCurtain
from switchbot.devices.device import (
    DEVICE_GET_BASIC_SETTINGS_KEY,
    CharacteristicMissingError,
    SwitchbotOperationError,
)

from .test_adv_parser import generate_ble_device
from .test_curtain import make_advertisement_data

BASIC = bytes([1, 80, 10, 2, 0x40, 4, 40, 0])
CHAIN = bytes([1, 0, 0, 2, 40, 80, 60, 0])
SUMMARY = bytes([1, 0x40, 0])
ADVANCED = bytes([1, 80, 10, 1, 0, 10, 4])


def diagnostic_device(reverse=False, model="Curtain 3"):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotCurtain(ble_device, reverse_mode=reverse)
    advertisement = make_advertisement_data(ble_device, False, 50)
    advertisement.data["modelFriendlyName"] = model
    device.update_from_advertisement(advertisement)
    replies = {
        DEVICE_GET_BASIC_SETTINGS_KEY: BASIC,
        CURTAIN_EXT_CHAIN_INFO_KEY: CHAIN,
        COVER_EXT_SUM_KEY: SUMMARY,
        COVER_EXT_ADV_KEY: ADVANCED,
    }

    async def reply(key, **kwargs):
        return replies[key]

    device._send_command = AsyncMock(side_effect=reply)
    return device, replies


@pytest.mark.asyncio
@pytest.mark.parametrize("code", range(7))
async def test_charging_codes(code):
    device, replies = diagnostic_device()
    replies[COVER_EXT_ADV_KEY] = bytes([1, 80, 10, code, 0, 10, code])
    assert await device.refresh_diagnostics()
    for slot in ("device0", "device1"):
        assert (
            device.ext_info_adv[slot]["chargingState"]
            is list(CurtainChargingState)[code]
        )
        assert device.ext_info_adv[slot]["chargingStateRaw"] == code


@pytest.mark.asyncio
async def test_unknown_charging_code():
    device, replies = diagnostic_device()
    replies[COVER_EXT_ADV_KEY] = bytes([1, 80, 10, 255, 0, 10, 255])
    assert await device.refresh_diagnostics()
    assert device.ext_info_adv["device0"]["chargingState"] is None
    assert device.ext_info_adv["device0"]["stateOfCharge"] is None
    assert device.ext_info_adv["device0"]["chargingStateRaw"] == 255


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "response"),
    [
        ("get_basic_info", BASIC),
        ("get_extended_chain_info", CHAIN),
        ("get_extended_info_summary", SUMMARY),
        ("get_extended_info_adv", ADVANCED),
    ],
)
async def test_every_truncated_length_and_rejected_response(method, response):
    device, _ = diagnostic_device()
    assert await device.refresh_diagnostics()
    before = dict(device.diagnostic_timestamps)
    old_summary = dict(device.ext_info_sum)
    old_advanced = dict(device.ext_info_adv)
    for length in range(len(response)):
        device._send_command = AsyncMock(return_value=response[:length])
        assert await getattr(device, method)() is None
    for status in (0, 2, 3, 4, 5, 6, 7, 9, 13, 14, 255):
        device._send_command = AsyncMock(return_value=bytes([status]) + response[1:])
        assert await getattr(device, method)() is None
    assert device.diagnostic_timestamps == before
    assert device.ext_info_sum == old_summary
    assert device.ext_info_adv == old_advanced


@pytest.mark.asyncio
async def test_invalid_page_preserves_other_successes():
    device, replies = diagnostic_device()
    replies[COVER_EXT_SUM_KEY] = b"\x05"
    callback = Mock()
    device.subscribe(callback)
    assert not await device.refresh_diagnostics()
    assert "summary" not in device.diagnostic_timestamps
    assert set(device.diagnostic_timestamps) == {"basic", "chain", "advanced"}
    assert device.get_position() == 40
    callback.assert_called_once_with()


@pytest.mark.asyncio
async def test_explicit_transport_error_propagates_and_notifies():
    device, _ = diagnostic_device()
    callback = Mock()
    device.subscribe(callback)
    device._send_command = AsyncMock(side_effect=BleakError("Disconnected"))
    with pytest.raises(BleakError):
        await device.refresh_diagnostics()
    callback.assert_called_once_with()


@pytest.mark.parametrize("interval", [0, -1, True, 1.5, "900"])
def test_invalid_interval(interval):
    device, _ = diagnostic_device()
    with pytest.raises(ValueError, match="positive integer"):
        device.set_diagnostics_interval(interval)


@pytest.mark.asyncio
async def test_default_updates_only_read_basic():
    device, _ = diagnostic_device()
    await device.update()
    device._send_command.assert_awaited_once_with(
        key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=3
    )


@pytest.mark.asyncio
async def test_refresh_cadence_independent_of_advertisements():
    device, _ = diagnostic_device()
    device.set_diagnostics_interval(900)
    with patch("switchbot.devices.curtain.time.monotonic", return_value=1000):
        assert device.poll_needed(None)
        assert not device.poll_needed(0)
        await device.update()
    assert device._send_command.await_count == 5
    device._send_command.reset_mock()
    with patch("switchbot.devices.curtain.time.monotonic", return_value=1899):
        device.update_from_advertisement(device._sb_adv_data)
        assert not device.poll_needed(899)
        await device.update()
    assert device._send_command.await_count == 1
    with patch("switchbot.devices.curtain.time.monotonic", return_value=1900):
        device.update_from_advertisement(device._sb_adv_data)
        assert device.poll_needed(900)
        await device.update()
    assert device._send_command.await_count == 6
    device.set_diagnostics_interval(None)
    device._send_command.reset_mock()
    await device.update()
    assert device._send_command.await_count == 1


@pytest.mark.asyncio
async def test_movement_defers_diagnostics():
    device, replies = diagnostic_device()
    replies[DEVICE_GET_BASIC_SETTINGS_KEY] = bytes([1, 80, 10, 2, 0x40, 5, 40, 0])
    device.set_diagnostics_interval(900)
    await device.update()
    assert device._send_command.await_count == 1
    replies[DEVICE_GET_BASIC_SETTINGS_KEY] = BASIC
    await device.update()
    assert device._send_command.await_count == 6


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [BleakError, TimeoutError, CharacteristicMissingError, SwitchbotOperationError],
)
async def test_optional_transport_failure_preserves_command_success_and_throttles(
    failure,
):
    device, replies = diagnostic_device()
    device.set_diagnostics_interval(900)
    device._send_multiple_commands = AsyncMock(return_value=True)

    async def reply(key, **kwargs):
        if key == CURTAIN_EXT_CHAIN_INFO_KEY:
            raise failure("Disconnected")
        return replies[key]

    device._send_command.side_effect = reply
    with patch("switchbot.devices.curtain.time.monotonic", return_value=1000):
        assert await device.open(1)
        assert not device.poll_needed(0)
    with patch("switchbot.devices.curtain.time.monotonic", return_value=1900):
        assert device.poll_needed(900)


@pytest.mark.asyncio
async def test_basic_callback_before_optional_diagnostics():
    device, _ = diagnostic_device()
    device.set_diagnostics_interval(900)
    observations = []
    device.subscribe(lambda: observations.append(set(device.diagnostic_timestamps)))
    await device.update()
    assert observations[0] == {"basic"}
    assert observations[-1] == {"basic", "chain", "summary", "advanced"}


@pytest.mark.asyncio
async def test_older_curtain_never_automatically_reads_extended_pages():
    device, _ = diagnostic_device(model="Curtain")
    device.set_diagnostics_interval(900)
    await device.update()
    assert device._send_command.await_count == 1
    assert not await device.refresh_diagnostics()


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("speed", [1, 255])
async def test_speed_command_bytes(reverse, speed):
    device, _ = diagnostic_device(reverse)
    device._send_multiple_commands = AsyncMock(return_value=True)
    device.update = AsyncMock()
    assert await device.open(speed)
    device._send_multiple_commands.assert_awaited_with(
        ["570f4501010100", f"570f450105{speed:02X}00"]
    )
    assert await device.close(speed)
    device._send_multiple_commands.assert_awaited_with(
        ["570f4501010164", f"570f450105{speed:02X}64"]
    )
    assert await device.set_position(25, speed)
    position = 75 if reverse else 25
    device._send_multiple_commands.assert_awaited_with(
        [f"570f45010101{position:02X}", f"570f450105{speed:02X}{position:02X}"]
    )
    assert await device.stop()
    device._send_multiple_commands.assert_awaited_with(["570f45010001", "570f450100ff"])


@pytest.mark.asyncio
async def test_invalid_chain_percentages_remain_unknown():
    device, replies = diagnostic_device()
    replies[CURTAIN_EXT_CHAIN_INFO_KEY] = bytes([1, 0, 0, 2, 127, 127, 127, 127])
    info = await device.get_extended_chain_info()
    assert info["chainLength"] == 2
    for slot in ("device0", "device1"):
        assert info[slot]["position"] is None
        assert info[slot]["battery"] is None
    assert "chain" in device.diagnostic_timestamps
