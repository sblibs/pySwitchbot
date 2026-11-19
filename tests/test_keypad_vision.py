"""Test keypad vision series device parsing and functionality."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement
from switchbot.devices.device import SwitchbotEncryptedDevice
from switchbot.devices.keypad_vision import (
    COMMAND_GET_PASSWORD_COUNT,
    UPDATE_RETRY_INTERVAL,
    SwitchbotKeypadVision,
)

from . import KEYPAD_VISION_INFO, KEYPAD_VISION_PRO_INFO
from .test_adv_parser import AdvTestCase, generate_ble_device


def create_device_for_command_testing(
    adv_info: AdvTestCase,
    init_data: dict | None = None,
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotKeypadVision(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=adv_info.modelName
    )

    device._send_command = AsyncMock()
    device._send_command_sequence = AsyncMock()
    device.update = AsyncMock()
    device.update_from_advertisement(
        make_advertisement_data(ble_device, adv_info, init_data)
    )
    return device


def make_advertisement_data(
    ble_device: BLEDevice, adv_info: AdvTestCase, init_data: dict | None = None
):
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


def create_device_for_update_testing(adv_info: AdvTestCase) -> SwitchbotKeypadVision:
    """Create a device whose update() is the real one."""
    device = create_device_for_command_testing(adv_info)
    del device.update
    device._get_basic_info = AsyncMock()
    return device


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adv_info"),
    [
        (KEYPAD_VISION_INFO),
        (KEYPAD_VISION_PRO_INFO),
    ],
)
async def test_get_basic_info_none(adv_info: AdvTestCase) -> None:
    """Test getting basic info returns None when no data."""
    device = create_device_for_command_testing(adv_info)
    device._get_basic_info = AsyncMock(return_value=None)

    info = await device.get_basic_info()
    assert info is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adv_info", "basic_info", "result"),
    [
        (
            KEYPAD_VISION_INFO,
            b"\x01_\x18\x16\x01\x02\x00\n\x01\x02\x03\x05\x02\x00\x01\x00",
            [95, 2.4, 22, 1, True, True, True, 5, True, False],
        ),
        (
            KEYPAD_VISION_PRO_INFO,
            b"\x01_\x0b\x18\x01\x02\x00\n\x01\x02\x03\x05\x02\x00\x03\x00",
            [95, 1.1, 24, 1, True, True, True, 5, True, True],
        ),
    ],
)
async def test_get_basic_info(
    adv_info: AdvTestCase, basic_info: bytes, result: dict
) -> None:
    """Test getting basic info from Keypad Vision devices."""
    device = create_device_for_command_testing(adv_info)
    device._get_basic_info = AsyncMock(return_value=basic_info)

    info = await device.get_basic_info()
    assert info["battery"] == result[0]
    assert info["firmware"] == result[1]
    assert info["hardware"] == result[2]
    assert info["support_fingerprint"] == result[3]
    assert info["lock_button_enabled"] == result[4]
    assert info["tamper_alarm_enabled"] == result[5]
    assert info["backlight_enabled"] == result[6]
    assert info["backlight_level"] == result[7]
    assert info["prompt_tone_enabled"] == result[8]
    assert info["battery_charging"] == result[9]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adv_info",
    [
        KEYPAD_VISION_INFO,
        KEYPAD_VISION_PRO_INFO,
    ],
)
async def test_add_invalid_password(adv_info: AdvTestCase) -> None:
    """Test adding an invalid password raises ValueError."""
    device = create_device_for_command_testing(adv_info)

    invalid_passwords = ["123", "abcdef", "1234567890123", "12 3456", "passw0rd!"]

    for password in invalid_passwords:
        with pytest.raises(ValueError, match=r"Password must be 6-12 digits."):
            await device.add_password(password)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adv_info",
    [
        KEYPAD_VISION_INFO,
        KEYPAD_VISION_PRO_INFO,
    ],
)
@pytest.mark.parametrize(
    ("password", "expected_payload"),
    [
        (
            "123456",
            ["570F52020210FF0006010203040506"],
        ),
        (
            "123456789012",
            ["570F52020220FF000C0102030405060708", "570F5202022109000102"],
        ),
    ],
)
async def test_add_password(
    adv_info: AdvTestCase, password: str, expected_payload: list[str]
) -> None:
    """Test adding a valid password sends correct command."""
    device = create_device_for_command_testing(adv_info)

    await device.add_password(password)

    device._send_command_sequence.assert_awaited_once_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adv_info",
    [
        KEYPAD_VISION_INFO,
        KEYPAD_VISION_PRO_INFO,
    ],
)
async def test_get_password_count_no_response(adv_info: AdvTestCase) -> None:
    """Test getting password count returns None when no response."""
    device = create_device_for_command_testing(adv_info)

    device._send_command.return_value = None

    result = await device.get_password_count()
    device._send_command.assert_awaited_once_with(COMMAND_GET_PASSWORD_COUNT)

    assert result is None


@pytest.mark.asyncio
async def test_get_password_count_for_keypad_vision_pro() -> None:
    """Test getting password count for Keypad Vision Pro."""
    device = create_device_for_command_testing(KEYPAD_VISION_PRO_INFO)

    device._send_command.return_value = bytes(
        [0x01, 0x05, 0x02, 0x03, 0x00, 0x02, 0x01, 0x00]
    )

    result = await device.get_password_count()
    device._send_command.assert_awaited_once_with(COMMAND_GET_PASSWORD_COUNT)

    assert result == {
        "pin": 5,
        "nfc": 2,
        "fingerprint": 3,
        "duress_pin": 0,
        "duress_fingerprint": 2,
        "face": 1,
        "palm_vein": 0,
    }


@pytest.mark.asyncio
async def test_get_password_count_for_keypad_vision() -> None:
    """Test getting password count for Keypad Vision."""
    device = create_device_for_command_testing(KEYPAD_VISION_INFO)

    device._send_command.return_value = bytes([0x01, 0x03, 0x02, 0x01, 0x01, 0x00])

    result = await device.get_password_count()
    device._send_command.assert_awaited_once_with(COMMAND_GET_PASSWORD_COUNT)

    assert result == {
        "pin": 3,
        "nfc": 2,
        "fingerprint": 1,
        "duress_pin": 1,
        "duress_fingerprint": 0,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adv_info",
    [
        KEYPAD_VISION_INFO,
        KEYPAD_VISION_PRO_INFO,
    ],
)
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(
    mock_parent_verify: AsyncMock, adv_info: AdvTestCase
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await SwitchbotKeypadVision.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
        model=adv_info.modelName,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        adv_info.modelName,
    )

    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize("adv_info", [KEYPAD_VISION_INFO, KEYPAD_VISION_PRO_INFO])
@pytest.mark.parametrize("reply_length", [1, 2, 14])
async def test_get_basic_info_short_reply(
    adv_info: AdvTestCase, reply_length: int
) -> None:
    """A reply shorter than the basic info layout returns None, not IndexError."""
    device = create_device_for_command_testing(adv_info)
    device._get_basic_info = AsyncMock(return_value=b"\x04" * reply_length)

    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adv_info", "reply"),
    [
        (KEYPAD_VISION_INFO, b"\x04"),
        (KEYPAD_VISION_INFO, bytes([0x01, 0x03, 0x02, 0x01, 0x01])),
        (KEYPAD_VISION_PRO_INFO, b"\x04"),
        (KEYPAD_VISION_PRO_INFO, bytes([0x01, 0x05, 0x02, 0x03, 0x00, 0x02, 0x01])),
    ],
)
async def test_get_password_count_short_reply(
    adv_info: AdvTestCase, reply: bytes
) -> None:
    """A reply shorter than the password count layout returns None."""
    device = create_device_for_command_testing(adv_info)
    device._send_command.return_value = reply

    assert await device.get_password_count() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("adv_info", [KEYPAD_VISION_INFO, KEYPAD_VISION_PRO_INFO])
async def test_update_backs_off_after_short_reply(adv_info: AdvTestCase) -> None:
    """A failed update is not retried until the retry interval has passed."""
    device = create_device_for_update_testing(adv_info)
    device._get_basic_info.return_value = b"\x04"

    with patch("switchbot.devices.keypad_vision.time.monotonic") as monotonic:
        monotonic.return_value = 1000.0
        await device.update()
        await device.update()
        assert device._get_basic_info.await_count == 1

        monotonic.return_value = 1000.0 + UPDATE_RETRY_INTERVAL - 1
        await device.update()
        assert device._get_basic_info.await_count == 1

        monotonic.return_value = 1000.0 + UPDATE_RETRY_INTERVAL
        await device.update()
        assert device._get_basic_info.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("adv_info", [KEYPAD_VISION_INFO, KEYPAD_VISION_PRO_INFO])
async def test_update_backs_off_after_exception(adv_info: AdvTestCase) -> None:
    """An update that raises is also not retried straight away."""
    device = create_device_for_update_testing(adv_info)
    device._get_basic_info.side_effect = TimeoutError

    with patch("switchbot.devices.keypad_vision.time.monotonic") as monotonic:
        monotonic.return_value = 1000.0
        with pytest.raises(TimeoutError):
            await device.update()
        await device.update()
        assert device._get_basic_info.await_count == 1


@pytest.mark.asyncio
async def test_update_without_failure_does_not_back_off() -> None:
    """Successful updates are never skipped."""
    device = create_device_for_update_testing(KEYPAD_VISION_INFO)
    device._get_basic_info.return_value = (
        b"\x01_\x18\x16\x01\x02\x00\n\x01\x02\x03\x05\x02\x00\x01\x00"
    )

    with patch("switchbot.devices.keypad_vision.time.monotonic") as monotonic:
        monotonic.return_value = 1000.0
        await device.update()
        await device.update()
        assert device._get_basic_info.await_count == 2


@pytest.mark.asyncio
async def test_sequence_change_does_not_loop_on_short_reply() -> None:
    """New sequence numbers after a failed update do not each trigger a connection."""
    device = create_device_for_update_testing(KEYPAD_VISION_PRO_INFO)
    device._get_basic_info.return_value = b"\x04"
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")

    tasks = []
    with patch(
        "switchbot.devices.device.create_background_task",
        side_effect=lambda coro: tasks.append(asyncio.ensure_future(coro)),
    ):
        for sequence_number in range(1, 5):
            device.update_from_advertisement(
                make_advertisement_data(
                    ble_device,
                    KEYPAD_VISION_PRO_INFO,
                    {"sequence_number": sequence_number},
                )
            )
            await asyncio.gather(*tasks)

    assert len(tasks) == 4
    assert device._get_basic_info.await_count == 1
