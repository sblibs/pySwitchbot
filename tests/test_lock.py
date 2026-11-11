import logging
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from switchbot import SwitchbotLockUltra, SwitchbotModel
from switchbot.const.lock import LockStatus, QuickKeyFunction
from switchbot.devices import lock
from switchbot.devices.device import SwitchbotOperationError
from switchbot.models import SwitchBotAdvertisement

from .test_adv_parser import generate_ble_device


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("replies", "valid"),
    [
        (
            [bytes.fromhex("01 88 00 00 00 00 00"), bytes.fromhex("01 85 28 21 14")],
            True,
        ),
        ([None], False),
        ([bytes.fromhex("01 88 00 00 00 00 00"), None], False),
    ],
)
async def test_uwb_lock_key_verification(replies, valid):
    device = generate_ble_device("aa:bb:cc:dd:ee:ff", "UWB Lock")
    with patch.object(SwitchbotLockUltra, "_send_command", side_effect=replies) as send:
        assert (
            await SwitchbotLockUltra.verify_encryption_key(
                device, "ff", "ff" * 16, SwitchbotModel.UWB_LOCK
            )
            is valid
        )
    assert [args.kwargs["key"] for args in send.await_args_list] == [
        "570f4f8107",
        "5702",
    ][: len(replies)]


@pytest.mark.asyncio
async def test_nano_update_reads_lock_and_basic_info():
    device = create_device_for_command_testing(SwitchbotModel.LOCK_NANO)
    device.update_from_advertisement(
        SwitchBotAdvertisement(
            device._device.address, {"data": {"battery": 95}}, device._device, -60
        )
    )
    replies = [bytes.fromhex("01 90 08 5f 00 00 40"), bytes.fromhex("01 4b 21 14")]
    with patch.object(device, "_send_command", side_effect=replies) as send:
        await device.update()

    assert send.await_args_list == [
        call(key="570f4f810c", retry=device._retry_count),
        call(key="5702", retry=device._retry_count),
    ]
    assert device.get_lock_status() is LockStatus.LOCKING
    assert device.is_calibrated()
    assert device.is_auto_lock_paused()
    assert device.is_unlocked_alarm_on()
    assert device.get_battery_percent() == 75
    assert device.parsed_data["firmware"] == 3.3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response", [None, bytes.fromhex("01"), bytes.fromhex("01 f8 00 00 00 00 00")]
)
async def test_nano_rejects_invalid_status_during_key_verification(response):
    device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Lock Nano")
    with patch.object(lock.SwitchbotLock, "_send_command", return_value=response):
        assert not await lock.SwitchbotLock.verify_encryption_key(
            device, "ff", "ffffffffffffffffffffffffffffffff", SwitchbotModel.LOCK_NANO
        )


@pytest.mark.asyncio
async def test_nano_lock_info_command():
    device = create_device_for_command_testing(SwitchbotModel.LOCK_NANO)
    with patch.object(device, "_send_command", return_value=b"\x01\x00") as send:
        assert await device._get_lock_info() == b"\x01\x00"
    send.assert_awaited_once_with(key="570f4f810c", retry=device._retry_count)


@pytest.mark.asyncio
async def test_nano_notification_command():
    device = create_device_for_command_testing(SwitchbotModel.LOCK_NANO)
    with patch.object(device, "_send_command", return_value=b"\x01\x00") as send:
        assert await device._enable_notifications()
    send.assert_awaited_once_with("570e01001e0000810c")


def create_device_for_command_testing(model: str, cls=lock.SwitchbotLock):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    return cls(ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=model)


def test_nano_status_notification_updates_device():
    device = create_device_for_command_testing(SwitchbotModel.LOCK_NANO)
    advertisement = SwitchBotAdvertisement(
        device._device.address,
        {"data": {"status": LockStatus.UNLOCKED}},
        device._device,
        -60,
    )
    device.update_from_advertisement(advertisement)
    received = []
    device.subscribe(lambda: received.append(device.get_lock_status()))

    payload = bytes.fromhex("90 00 00 00 00 00")
    with (
        patch.object(device, "_decrypt", return_value=payload) as decrypt,
        patch.object(device, "_reset_disconnect_timer"),
    ):
        frame = bytearray.fromhex("0f 00 00 00 12 34 56 78 9a bc")
        device._notification_handler(0, frame)

    decrypt.assert_called_once_with(frame[4:])
    assert received == [LockStatus.LOCKING]
    assert device.get_lock_status() is LockStatus.LOCKING


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_ULTRA_MAX,
        SwitchbotModel.UWB_LOCK,
        SwitchbotModel.LOCK_NANO,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_lock_init(model: str):
    """Test the initialization of the lock device."""
    device = create_device_for_command_testing(model)
    assert device._model == model


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.AIR_PURIFIER_JP,
    ],
)
def test_lock_init_with_invalid_model(model: str):
    """Test that initializing with an invalid model raises ValueError."""
    with pytest.raises(
        ValueError, match="initializing SwitchbotLock with a non-lock model"
    ):
        create_device_for_command_testing(model)


def test_ultra_direct_construction():
    device = generate_ble_device("aa:bb:cc:dd:ee:ff", "lock")
    assert (
        SwitchbotLockUltra(device, "ff", "ff" * 16)._model is SwitchbotModel.LOCK_ULTRA
    )


def test_default_model_classvar():
    """The classvar default is SwitchbotModel.LOCK."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = lock.SwitchbotLock(ble_device, "ff", "ffffffffffffffffffffffffffffffff")
    assert device._model == SwitchbotModel.LOCK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "command"),
    [
        (SwitchbotModel.LOCK, b"W\x0fN\x01\x01\x10\x80"),
        (SwitchbotModel.LOCK_LITE, b"W\x0fN\x01\x01\x10\x81"),
        (SwitchbotModel.LOCK_PRO, b"W\x0fN\x01\x01\x10\x85"),
        (SwitchbotModel.LOCK_ULTRA, b"W\x0fN\x01\x01\x10\x86"),
        (SwitchbotModel.LOCK_ULTRA_MAX, b"W\x0fN\x01\x01\x00\x00"),
        (SwitchbotModel.UWB_LOCK, b"W\x0fN\x01\x01\x00\x00"),
        (SwitchbotModel.LOCK_NANO, b"W\x0fN\x01\x01\x00\x00"),
        (SwitchbotModel.LOCK_VISION, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.LOCK_VISION_PRO, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.LOCK_PRO_WIFI, b"W\x0fN\x01\x01\x10\x82"),
    ],
)
async def test_lock(model: str, command: bytes):
    """Test lock method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.UNLOCKED)
    with (
        patch.object(
            device, "_send_command", return_value=b"\x01\x00"
        ) as mock_send_command,
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00\x64\x01"),
    ):
        result = await device.lock()
        assert result is True
        mock_send_command.assert_any_call(lock.COMMAND_LOCK[model])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "command"),
    [
        (SwitchbotModel.LOCK, b"W\x0fN\x01\x01\x10\x80"),
        (SwitchbotModel.LOCK_LITE, b"W\x0fN\x01\x01\x10\x81"),
        (SwitchbotModel.LOCK_PRO, b"W\x0fN\x01\x01\x10\x84"),
        (SwitchbotModel.LOCK_ULTRA, b"W\x0fN\x01\x01\x10\x83"),
        (SwitchbotModel.LOCK_ULTRA_MAX, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.UWB_LOCK, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.LOCK_NANO, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.LOCK_VISION, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.LOCK_VISION_PRO, b"W\x0fN\x01\x01\x00\x80"),
        (SwitchbotModel.LOCK_PRO_WIFI, b"W\x0fN\x01\x01\x10\x81"),
    ],
)
async def test_unlock(model: str, command: bytes):
    """Test unlock method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.LOCKED)
    with (
        patch.object(
            device, "_send_command", return_value=b"\x01\x00"
        ) as mock_send_command,
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00\x64\x01"),
    ):
        result = await device.unlock()
        assert result is True
        mock_send_command.assert_any_call(lock.COMMAND_UNLOCK[model])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_ULTRA_MAX,
        SwitchbotModel.UWB_LOCK,
        SwitchbotModel.LOCK_NANO,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_unlock_without_unlatch(model: str):
    """Test unlock_without_unlatch method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.LOCKED)
    with (
        patch.object(device, "_send_command", return_value=b"\x01\x00"),
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00\x64\x01"),
    ):
        result = await device.unlock_without_unlatch()
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_NANO,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_ULTRA_MAX,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_get_basic_info(model: str):
    """Test get_basic_info method."""
    device = create_device_for_command_testing(model)
    lock_data = b"\x00\x80\x00\x00\x00\x00\x00\x00"
    basic_data = bytes.fromhex("01 64 01 21 14")
    with (
        patch.object(device, "_get_lock_info", return_value=lock_data),
        patch.object(device, "_get_basic_info", return_value=basic_data),
    ):
        result = await device.get_basic_info()
        assert result is not None
        assert "battery" in result
        assert "firmware" in result
        assert "calibration" in result
        assert "status" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_NANO,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_get_basic_info_no_lock_data(model: str):
    """Test get_basic_info when no lock data is returned."""
    device = create_device_for_command_testing(model)
    with patch.object(device, "_get_lock_info", return_value=None):
        result = await device.get_basic_info()
        assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_NANO,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_get_basic_info_no_basic_data(model: str):
    """Test get_basic_info when no basic data is returned."""
    device = create_device_for_command_testing(model)
    lock_data = b"\x00\x80\x00\x00\x00\x00\x00\x00"
    with (
        patch.object(device, "_get_lock_info", return_value=lock_data),
        patch.object(device, "_get_basic_info", return_value=None),
    ):
        result = await device.get_basic_info()
        assert result is None


@pytest.mark.parametrize("battery", [100, 255])
def test_parse_basic_data(battery):
    """Test _parse_basic_data method."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK)
    basic_data = bytes([0, battery, 1])
    result = device._parse_basic_data(basic_data)
    assert result["battery"] == battery
    assert result["firmware"] == 0.1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [SwitchbotModel.LOCK_ULTRA, SwitchbotModel.LOCK_ULTRA_MAX, SwitchbotModel.UWB_LOCK],
)
@pytest.mark.parametrize(
    ("basic_info", "battery", "firmware"),
    [
        ("01 4b 28 21 14", 75, 3.3),  # Main battery in use.
        ("01 85 28 21 14", 40, 3.3),  # Backup battery in use.
        ("01 f3 28 21 14", 40, 3.3),  # Byte 1 must never appear as 243%.
        ("01 80 ff 21 14", 255, 3.3),  # Report the backup battery byte as received.
        ("01 4b 28", 60, 2.1),  # Truncated reply: keep the last readings.
    ],
)
async def test_lock2_basic_info(model, basic_info, battery, firmware):
    device = create_device_for_command_testing(model, SwitchbotLockUltra)
    device.update_from_advertisement(
        SwitchBotAdvertisement(
            device._device.address,
            {"data": {"battery": 60, "firmware": 2.1}},
            device._device,
            -60,
        )
    )
    with (
        patch.object(
            device, "_get_lock_info", return_value=bytes.fromhex("01 80 00 00 00 00 00")
        ),
        patch.object(device, "_get_basic_info", return_value=bytes.fromhex(basic_info)),
    ):
        await device.update()

    assert device.get_battery_percent() == battery
    assert device.parsed_data["firmware"] == firmware
    assert device.get_lock_status() is LockStatus.LOCKED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [SwitchbotModel.LOCK_ULTRA, SwitchbotModel.LOCK_ULTRA_MAX, SwitchbotModel.UWB_LOCK],
)
async def test_lock2_battery_after_lock(model):
    device = create_device_for_command_testing(model, SwitchbotLockUltra)
    device.update_from_advertisement(
        SwitchBotAdvertisement(
            device._device.address,
            {"data": {"status": LockStatus.UNLOCKED}},
            device._device,
            -60,
        )
    )
    with (
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_send_command", return_value=bytes.fromhex("01")),
        patch.object(
            device, "_get_basic_info", return_value=bytes.fromhex("01 f3 28 21 14")
        ),
    ):
        assert await device.lock()

    assert device.get_battery_percent() == 40
    assert device.parsed_data["firmware"] == 3.3


@pytest.mark.asyncio
async def test_lock_ultra_max_verifies_encryption_key():
    """Lock Ultra Max verifies a valid encryption key."""
    lock_data = b"\x00\x80\x00\x00\x00\x00\x00\x00"
    basic_data = bytes.fromhex("01 64 01 21 14")
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    with (
        patch.object(lock.SwitchbotLock, "_get_lock_info", return_value=lock_data),
        patch.object(lock.SwitchbotLock, "_get_basic_info", return_value=basic_data),
    ):
        assert await SwitchbotLockUltra.verify_encryption_key(
            ble_device,
            "ff",
            "ffffffffffffffffffffffffffffffff",
            SwitchbotModel.LOCK_ULTRA_MAX,
        )


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_is_calibrated(model: str):
    """Test is_calibrated method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_calibrated() is True


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_get_lock_status(model: str):
    """Test get_lock_status method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.LOCKED)
    assert device.get_lock_status() == LockStatus.LOCKED


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_is_door_open(model: str):
    """Test is_door_open method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_door_open() is True


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_is_unclosed_alarm_on(model: str):
    """Test is_unclosed_alarm_on method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_unclosed_alarm_on() is True


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_is_unlocked_alarm_on(model: str):
    """Test is_unlocked_alarm_on method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_unlocked_alarm_on() is True


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
    ],
)
def test_is_auto_lock_paused(model: str):
    """Test is_auto_lock_paused method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_auto_lock_paused() is True


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_is_night_latch_enabled(model: str):
    """Test is_night_latch_enabled method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_night_latch_enabled() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_get_lock_info(model: str):
    """Test _get_lock_info method."""
    device = create_device_for_command_testing(model)
    expected_data = b"\x01\x00\x80\x00\x00\x00\x00\x00"
    with patch.object(device, "_send_command", return_value=expected_data):
        result = await device._get_lock_info()
        assert result == expected_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_get_lock_info_failure(model: str):
    """Test _get_lock_info method when command fails."""
    device = create_device_for_command_testing(model)
    with patch.object(device, "_send_command", return_value=b"\x00\x00"):
        result = await device._get_lock_info()
        assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_enable_notifications(model: str):
    """Test _enable_notifications method."""
    device = create_device_for_command_testing(model)
    with patch.object(device, "_send_command", return_value=b"\x01\x00"):
        result = await device._enable_notifications()
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_disable_notifications(model: str):
    """Test _disable_notifications method."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = True
    with patch.object(device, "_send_command", return_value=b"\x01\x00"):
        result = await device._disable_notifications()
        assert result is True
        assert device._notifications_enabled is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_disable_notifications_already_disabled(model: str):
    """Test _disable_notifications when already disabled."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = False
    with patch.object(device, "_send_command") as mock_send:
        result = await device._disable_notifications()
        assert result is True
        mock_send.assert_not_called()


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_notification_handler(model: str):
    """Test _notification_handler method."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = True
    data = bytearray(b"\x0f\x00\x00\x00\x80\x00\x00\x00\x00\x00")
    with patch.object(device, "_update_lock_status") as mock_update:
        device._notification_handler(0, data)
        mock_update.assert_called_once_with(data)


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_notification_handler_not_enabled(model: str):
    """Test _notification_handler when notifications not enabled."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = False
    data = bytearray(b"\x01\x00\x00\x00\x80\x00\x00\x00\x00\x00")
    with (
        patch.object(device, "_update_lock_status") as mock_update,
        patch.object(
            lock.SwitchbotSequenceDevice, "_notification_handler"
        ) as mock_super,
    ):
        device._notification_handler(0, data)
        mock_update.assert_not_called()
        mock_super.assert_called_once()


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_notification_handler_during_disconnect(
    model: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Test _notification_handler during expected disconnect."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = True
    device._expected_disconnect = True
    data = bytearray(b"\x0f\x00\x00\x00\x80\x00\x00\x00\x00\x00")
    with (
        patch.object(device, "_update_lock_status") as mock_update,
        caplog.at_level(logging.DEBUG),
    ):
        device._notification_handler(0, data)
        # Should not update lock status during disconnect
        mock_update.assert_not_called()
        # Should log debug message
        assert "Ignoring lock notification during expected disconnect" in caplog.text


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
def test_update_lock_status(model: str):
    """Test _update_lock_status method."""
    device = create_device_for_command_testing(model)
    data = bytearray(b"\x0f\x00\x00\x00\x80\x00\x00\x00\x00\x00")
    with (
        patch.object(device, "_decrypt", return_value=b"\x80\x00\x00\x00\x00\x00"),
        patch.object(device, "_update_parsed_data", return_value=True),
        patch.object(device, "_reset_disconnect_timer"),
        patch.object(device, "_fire_callbacks"),
    ):
        device._update_lock_status(data)


@pytest.mark.parametrize(
    ("model", "data", "expected"),
    [
        (
            SwitchbotModel.LOCK,
            b"\x80\x00\x00\x00\x00\x00",
            {
                "calibration": True,
                "status": LockStatus.LOCKED,  # (0x80 & 0b01110000) >> 4 = 0 = LOCKED
                "door_open": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
            },
        ),
        (
            SwitchbotModel.LOCK_LITE,
            b"\x80\x00\x00\x00\x00\x00",
            {
                "calibration": True,
                "status": LockStatus.LOCKED,  # (0x80 & 0b01110000) >> 4 = 0 = LOCKED
                "unlocked_alarm": False,
            },
        ),
        (
            SwitchbotModel.LOCK_PRO,
            b"\x80\x00\x00\x00\x00\x00",
            {
                "calibration": True,
                "status": LockStatus.LOCKED,  # (0x80 & 0b01111000) >> 3 = 0 = LOCKED
                "door_open": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
            },
        ),
        (
            SwitchbotModel.LOCK_ULTRA,
            b"\x88\x10\x00\x00\x00\xc0",
            {
                "calibration": True,
                "status": LockStatus.UNLOCKED,  # (0x88 & 0b01111000) >> 3 = 0x08 >> 3 = 1 = UNLOCKED
                "door_open": True,
                "unclosed_alarm": True,
                "unlocked_alarm": True,
                "half_lock_calibration": False,
            },
        ),
        (
            SwitchbotModel.LOCK_VISION,
            b"\x80\x00\x00\x00\x00\x00",
            {
                "calibration": True,
                "status": LockStatus.LOCKED,  # (0x80 & 0b01110000) >> 4 = 0 = LOCKED
                "unlocked_alarm": False,
            },
        ),
        (
            SwitchbotModel.LOCK_VISION_PRO,
            b"\x80\x00\x00\x00\x00\x00",
            {
                "calibration": True,
                "status": LockStatus.LOCKED,  # (0x80 & 0b01111000) >> 3 = 0 = LOCKED
                "door_open": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
            },
        ),
        (
            SwitchbotModel.LOCK_PRO_WIFI,
            b"\x80\x00\x00\x00\x00\x00",
            {
                "calibration": True,
                "status": LockStatus.LOCKED,  # (0x80 & 0b01111000) >> 3 = 0 = LOCKED
                "door_open": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
            },
        ),
    ],
)
def test_parse_lock_data(model: str, data: bytes, expected: dict):
    """Test _parse_lock_data static method."""
    result = lock.SwitchbotLock._parse_lock_data(data, model)
    assert result == expected


@pytest.mark.parametrize(
    ("model", "data", "expected"),
    [
        # Test LOCK with different status bits and flags
        (
            SwitchbotModel.LOCK,
            b"\x94\x00\x00\x00\x00\x00",  # Unlocked status (0x10 >> 4 = 1) with door open
            {
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "door_open": True,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
            },
        ),
        # Test LOCK_LITE without door_open field
        (
            SwitchbotModel.LOCK_LITE,
            b"\x90\x10\x00\x00\x00\x00",  # Unlocked with unlocked alarm
            {
                "calibration": True,
                "status": LockStatus.UNLOCKED,
                "unlocked_alarm": True,
            },
        ),
        # Test LOCK_PRO with new bit positions
        (
            SwitchbotModel.LOCK_PRO,
            b"\x90\x10\x00\x00\x00\xc0",  # New format: status bits 3-6, door open bit 4 of byte 1
            {
                "calibration": True,
                "status": LockStatus.LOCKING,  # (0x90 & 0b01111000) >> 3 = 0x10 >> 3 = 2 (LOCKING)
                "door_open": True,  # bit 4 of byte 1 (0x10)
                "unclosed_alarm": True,  # bit 7 of byte 5 (0xc0)
                "unlocked_alarm": True,  # bit 6 of byte 5 (0xc0)
            },
        ),
        # Test LOCK_ULTRA with same format as PRO
        (
            SwitchbotModel.LOCK_ULTRA,
            b"\x88\x00\x00\x00\x00\x40",  # Unlocked with unlocked alarm only
            {
                "calibration": True,
                "status": LockStatus.UNLOCKED,  # (0x88 & 0b01111000) >> 3 = 0x08 >> 3 = 1
                "door_open": False,
                "unclosed_alarm": False,
                "unlocked_alarm": True,  # bit 6 of byte 5
                "half_lock_calibration": False,
            },
        ),
        (
            SwitchbotModel.LOCK_PRO_WIFI,
            b"\x90\x10\x00\x00\x00\xc0",  # New format: status bits 3-6, door open bit 4 of byte 1
            {
                "calibration": True,
                "status": LockStatus.LOCKING,  # (0x90 & 0b01111000) >> 3 = 0x10 >> 3 = 2 (LOCKING)
                "door_open": True,  # bit 4 of byte 1 (0x10)
                "unclosed_alarm": True,  # bit 7 of byte 5 (0xc0)
                "unlocked_alarm": True,  # bit 6 of byte 5 (0xc0)
            },
        ),
    ],
)
def test_parse_lock_data_new_formats(model: str, data: bytes, expected: dict):
    """Test _parse_lock_data with new format changes."""
    result = lock.SwitchbotLock._parse_lock_data(data, model)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_lock_with_update(model: str):
    """Test lock method with status update."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(side_effect=[None, LockStatus.UNLOCKED])
    with (
        patch.object(device, "update", new_callable=AsyncMock),
        patch.object(device, "_send_command", return_value=b"\x01\x00"),
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00\x64\x01"),
    ):
        result = await device.lock()
        assert result is True


def test_is_half_lock_calibrated():
    """Test is_half_lock_calibrated method."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    device._get_adv_value = Mock(return_value=True)
    assert device.is_half_lock_calibrated() is True

    device._get_adv_value = Mock(return_value=False)
    assert device.is_half_lock_calibrated() is False


@pytest.mark.asyncio
async def test_half_lock_calibrated():
    """Test half_lock succeeds when calibrated."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    device._get_adv_value = Mock(side_effect=[True, LockStatus.LOCKED])
    with (
        patch.object(device, "_send_command", return_value=b"\x01\x00"),
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x01\x64\x01"),
    ):
        result = await device.half_lock()
        assert result is True


@pytest.mark.asyncio
async def test_half_lock_not_calibrated():
    """Test half_lock raises SwitchbotOperationError when not calibrated."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    device._get_adv_value = Mock(return_value=False)
    with pytest.raises(SwitchbotOperationError, match="not calibrated"):
        await device.half_lock()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA_MAX,
        SwitchbotModel.UWB_LOCK,
        SwitchbotModel.LOCK_NANO,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_half_lock_unsupported_model(model: str):
    """Test half_lock raises SwitchbotOperationError on unsupported models."""
    device = create_device_for_command_testing(model)
    with pytest.raises(SwitchbotOperationError, match="not supported"):
        await device.half_lock()


@pytest.mark.asyncio
async def test_half_lock():
    """Test half_lock method."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    device._get_adv_value = Mock(side_effect=[True, LockStatus.LOCKED])
    with (
        patch.object(device, "_send_command", return_value=b"\x01\x00") as mock_send,
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x01\x64\x01"),
    ):
        result = await device.half_lock()
        assert result is True
        mock_send.assert_awaited_once_with(
            lock.COMMAND_HALF_LOCK[SwitchbotModel.LOCK_ULTRA]
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "status"),
    [
        (SwitchbotModel.LOCK, LockStatus.LOCKED),
        (SwitchbotModel.LOCK_LITE, LockStatus.LOCKING),
        (SwitchbotModel.LOCK_PRO, LockStatus.LOCKED),
        (SwitchbotModel.LOCK_ULTRA, LockStatus.LOCKING),
        (SwitchbotModel.LOCK_VISION, LockStatus.LOCKED),
        (SwitchbotModel.LOCK_VISION_PRO, LockStatus.LOCKED),
        (SwitchbotModel.LOCK_PRO_WIFI, LockStatus.LOCKED),
    ],
)
async def test_lock_already_locked(model: str, status: LockStatus):
    """Test lock method when already locked."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=status)
    with patch.object(device, "_send_command") as mock_send:
        result = await device.lock()
        assert result is True
        mock_send.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
        SwitchbotModel.LOCK_VISION,
        SwitchbotModel.LOCK_VISION_PRO,
        SwitchbotModel.LOCK_PRO_WIFI,
    ],
)
async def test_lock_with_invalid_basic_data(model: str):
    """Test lock method with invalid basic data."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.UNLOCKED)
    with (
        patch.object(device, "_send_command", return_value=b"\x01\x00"),
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00"),
    ):
        result = await device.lock()
        assert result is True


@pytest.mark.asyncio
async def test_get_quick_key():
    """Reading the Quick Key parses the config byte (Lock Ultra)."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    # 0xca = enabled, single press, Lock & Unlock
    with patch.object(
        device, "_send_command", return_value=b"\x01\xca\x00\x00\x00\x80"
    ) as mock_send_command:
        result = await device.get_quick_key()
    mock_send_command.assert_any_call(
        key="570f4f0401",
        retry=device._retry_count,
    )
    assert result == {
        "raw": 0xCA,
        "light": True,
        "sound": True,
        "manual_unlock_linkage": False,
        "enabled": True,
        "double_press": False,
        "function": QuickKeyFunction.LOCK_AND_UNLOCK,
        "motor_speed": 0,
    }


@pytest.mark.asyncio
async def test_get_quick_key_failure():
    """A non-success status returns None."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(device, "_send_command", return_value=b"\x00"):
        assert await device.get_quick_key() is None


@pytest.mark.asyncio
async def test_get_quick_key_zero_properties():
    """A zero property byte means disabled, single press, and lock only."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(device, "_send_command", return_value=b"\x01\x00"):
        assert await device.get_quick_key() == {
            "raw": 0,
            "light": False,
            "sound": False,
            "manual_unlock_linkage": False,
            "enabled": False,
            "double_press": False,
            "function": QuickKeyFunction.LOCK_ONLY,
            "motor_speed": None,
        }


@pytest.mark.asyncio
async def test_set_quick_key_function_update_flag():
    """Bit 1 selects the entire two-bit function field for writing."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device,
        "_send_command",
        return_value=b"\x01\xc9",  # echo 0xc9 = Unlock Only
    ) as mock_send_command:
        result = await device.set_quick_key(function=QuickKeyFunction.UNLOCK_ONLY)
    mock_send_command.assert_awaited_once_with(
        key="570f4e0401000201ff", retry=device._retry_count
    )
    assert result is True


@pytest.mark.asyncio
async def test_set_quick_key_multiple_fields():
    """Update all Quick Key fields while keeping the default target and speed."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=b"\x01\xce"
    ) as mock_send_command:
        result = await device.set_quick_key(
            enabled=True, double_press=True, function=QuickKeyFunction.LOCK_AND_UNLOCK
        )
    mock_send_command.assert_awaited_once_with(
        key="570f4e0401000e0eff", retry=device._retry_count
    )
    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "flags_and_value"),
    [
        ({"enabled": False}, "0800"),
        ({"double_press": False}, "0400"),
        ({"function": QuickKeyFunction.LOCK_ONLY}, "0200"),
        (
            {
                "enabled": False,
                "double_press": False,
                "function": QuickKeyFunction.LOCK_ONLY,
            },
            "0e00",
        ),
    ],
)
async def test_set_quick_key_false_and_zero_values(
    kwargs: dict[str, Any], flags_and_value: str
):
    """Explicit false and zero values still select their fields for writing."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=b"\x01\xc0"
    ) as mock_send_command:
        result = await device.set_quick_key(**kwargs)
    mock_send_command.assert_awaited_once_with(
        key=f"570f4e040100{flags_and_value}ff", retry=device._retry_count
    )
    assert result is True


@pytest.mark.asyncio
async def test_set_quick_key_requires_a_field():
    """Calling with nothing to change raises ValueError."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with pytest.raises(ValueError, match="at least one setting"):
        await device.set_quick_key()


@pytest.mark.asyncio
async def test_quick_key_unsupported_model():
    """Quick Key is Lock Ultra only; other models raise."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK)
    with pytest.raises(SwitchbotOperationError):
        await device.get_quick_key()
    with pytest.raises(SwitchbotOperationError):
        await device.set_quick_key(enabled=True)


@pytest.mark.asyncio
async def test_get_quick_key_short_response():
    """A success status but a truncated payload returns None."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(device, "_send_command", return_value=b"\x01"):
        assert await device.get_quick_key() is None


@pytest.mark.asyncio
async def test_get_quick_key_unknown_function():
    """An undefined 2-bit function value keeps the bits that are unambiguous."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    # 0xcb = enabled, single press, function bits 0b11 (undefined)
    with patch.object(device, "_send_command", return_value=b"\x01\xcb"):
        assert await device.get_quick_key() == {
            "raw": 0xCB,
            "light": True,
            "sound": True,
            "manual_unlock_linkage": False,
            "enabled": True,
            "double_press": False,
            "function": None,
            "motor_speed": None,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("properties", "light", "sound"),
    [
        (0x0A, False, False),
        (0x4A, False, True),
        (0x8A, True, False),
        (0xCA, True, True),
    ],
)
async def test_get_quick_key_light_and_sound_settings(
    properties: int, light: bool, sound: bool
):
    """Read light and sound independently of the original Quick Key fields."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=bytes([1, properties, 0, 0, 0, 0])
    ):
        assert await device.get_quick_key() == {
            "raw": properties,
            "light": light,
            "sound": sound,
            "manual_unlock_linkage": False,
            "enabled": True,
            "double_press": False,
            "function": QuickKeyFunction.LOCK_AND_UNLOCK,
            "motor_speed": 0,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (b"\x01", False),
        (b"\x06", False),
        (b"\x01\x08", True),
        (b"\x06\x08", True),
        (b"\x01\x00", False),
        (b"\x06\x00", False),
        (b"\x00", False),
        (b"\x02", False),
        (b"\x03", False),
        (b"\x05", False),
    ],
)
async def test_set_quick_key_command_status(response: bytes, expected: bool):
    """Require a successful status and matching config without another read."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=response
    ) as mock_send_command:
        assert await device.set_quick_key(enabled=True) is expected

    mock_send_command.assert_awaited_once_with(
        key="570f4e0401000808ff", retry=device._retry_count
    )


@pytest.mark.asyncio
async def test_get_quick_key_manual_unlock_linkage_and_motor_speed():
    """Read primary properties and speed without using the secondary values."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=bytes([1, 0xD9, 0xFF, 2, 0, 0])
    ):
        assert await device.get_quick_key() == {
            "raw": 0xD9,
            "light": True,
            "sound": True,
            "manual_unlock_linkage": True,
            "enabled": True,
            "double_press": False,
            "function": QuickKeyFunction.UNLOCK_ONLY,
            "motor_speed": 2,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "command", "config"),
    [
        ({"light": True}, "570f4e0401008080ff", 0xCA),
        ({"light": False}, "570f4e0401008000ff", 0x4A),
        ({"sound": True}, "570f4e0401004040ff", 0xCA),
        ({"sound": False}, "570f4e0401004000ff", 0x8A),
        ({"manual_unlock_linkage": True}, "570f4e0401001010ff", 0xDA),
        ({"manual_unlock_linkage": False}, "570f4e0401001000ff", 0xCA),
    ],
)
async def test_set_quick_key_independent_properties(
    kwargs: dict[str, bool], command: str, config: int
):
    """Each basic property can be changed while retaining the Quick Key fields."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=bytes([1, config])
    ) as mock_send_command:
        assert await device.set_quick_key(**kwargs) is True

    mock_send_command.assert_awaited_once_with(key=command, retry=device._retry_count)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "command", "config"),
    [
        (
            {
                "light": True,
                "sound": False,
                "manual_unlock_linkage": True,
                "enabled": False,
                "double_press": True,
                "function": QuickKeyFunction.UNLOCK_ONLY,
            },
            "570f4e040100de95ff",
            0x95,
        ),
        (
            {
                "light": False,
                "sound": False,
                "manual_unlock_linkage": False,
                "enabled": False,
                "double_press": False,
                "function": QuickKeyFunction.LOCK_ONLY,
            },
            "570f4e040100de00ff",
            0x20,
        ),
    ],
)
async def test_set_quick_key_combines_all_properties(
    kwargs: dict[str, Any], command: str, config: int
):
    """Combine all writable config fields without selecting reserved bits."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=bytes([1, config])
    ) as mock_send_command:
        assert await device.set_quick_key(**kwargs) is True

    mock_send_command.assert_awaited_once_with(key=command, retry=device._retry_count)


@pytest.mark.asyncio
@pytest.mark.parametrize("motor_speed", [0, 1, 2])
async def test_set_quick_key_motor_speed(motor_speed: int):
    """Change speed alone with a single write command."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device,
        "_send_command",
        return_value=b"\x01\xca",
    ) as mock_send_command:
        assert await device.set_quick_key(motor_speed=motor_speed) is True

    mock_send_command.assert_awaited_once_with(
        key=f"570f4e0401000000{motor_speed:02x}", retry=device._retry_count
    )


@pytest.mark.asyncio
async def test_set_quick_key_motor_speed_with_other_properties():
    """Write speed and properties together without an additional read."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device,
        "_send_command",
        return_value=b"\x01\x5d",
    ) as mock_send_command:
        assert (
            await device.set_quick_key(
                light=False,
                sound=True,
                manual_unlock_linkage=True,
                enabled=True,
                double_press=True,
                function=QuickKeyFunction.UNLOCK_ONLY,
                motor_speed=2,
            )
            is True
        )

    mock_send_command.assert_awaited_once_with(
        key="570f4e040100de5d02", retry=device._retry_count
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("motor_speed", [-1, 3, 0x100])
async def test_set_quick_key_invalid_motor_speed(motor_speed: int):
    """Invalid speeds fail before Bluetooth commands are sent."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with (
        patch.object(device, "_send_command") as mock_send_command,
        pytest.raises(ValueError, match="motor_speed must be"),
    ):
        await device.set_quick_key(motor_speed=motor_speed)

    mock_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_set_quick_key_motor_speed_keep():
    """Explicit 0xFF preserves speed without an additional read."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=b"\x01\xca"
    ) as mock_send_command:
        assert await device.set_quick_key(light=True, motor_speed=0xFF) is True

    mock_send_command.assert_awaited_once_with(
        key="570f4e0401008080ff", retry=device._retry_count
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "config", "reported"),
    [
        ({"light": True}, 0x00, False),
        ({"light": False}, 0x80, True),
        ({"sound": True}, 0x00, False),
        ({"manual_unlock_linkage": True}, 0x00, False),
        ({"enabled": False}, 0x08, True),
        ({"double_press": True}, 0x00, False),
        ({"function": QuickKeyFunction.LOCK_ONLY}, 0x01, QuickKeyFunction.UNLOCK_ONLY),
        ({"function": QuickKeyFunction.UNLOCK_ONLY}, 0x00, QuickKeyFunction.LOCK_ONLY),
        ({"function": QuickKeyFunction.LOCK_AND_UNLOCK}, 0x03, None),
    ],
)
async def test_set_quick_key_config_mismatch(
    kwargs: dict[str, Any],
    config: int,
    reported: bool | QuickKeyFunction | None,
    caplog: pytest.LogCaptureFixture,
):
    """Identify the rejected field, requested value, and reported value."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(
        device, "_send_command", return_value=bytes([1, config])
    ) as mock_send_command:
        assert await device.set_quick_key(**kwargs) is False

    mock_send_command.assert_awaited_once()
    setting, expected = next(iter(kwargs.items()))
    assert (
        f"Quick Key {setting} was not applied "
        f"(requested={expected}, reported={reported}, config={config:#04x})"
    ) in caplog.text


@pytest.mark.asyncio
async def test_set_quick_key_multiple_config_mismatches(
    caplog: pytest.LogCaptureFixture,
):
    """Report every mismatching field in a combined write."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(device, "_send_command", return_value=b"\x01\x00"):
        assert (
            await device.set_quick_key(
                light=True,
                sound=True,
                manual_unlock_linkage=True,
                enabled=True,
                double_press=True,
                function=QuickKeyFunction.UNLOCK_ONLY,
            )
            is False
        )

    messages = [
        record.message
        for record in caplog.records
        if "was not applied" in record.message
    ]
    assert len(messages) == 6
    for setting in (
        "light",
        "sound",
        "manual_unlock_linkage",
        "enabled",
        "double_press",
        "function",
    ):
        assert any(
            f"Quick Key {setting} was not applied" in message for message in messages
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [0x00, 0x02, 0x03, 0x04, 0x05, 0x09, 0x0E])
async def test_set_quick_key_failed_status_logs_code(
    status: int, caplog: pytest.LogCaptureFixture
):
    """Keep the device status code in diagnostics for rejected commands."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(device, "_send_command", return_value=bytes([status])):
        assert await device.set_quick_key(enabled=True) is False

    assert (
        f"Quick Key command failed (status={status:#04x}, response={status:02x})"
        in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [0x01, 0x06])
async def test_set_quick_key_missing_config_logs_status(
    status: int, caplog: pytest.LogCaptureFixture
):
    """Distinguish a missing config from a rejected command."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with patch.object(device, "_send_command", return_value=bytes([status])):
        assert await device.set_quick_key(enabled=True) is False

    assert (
        f"Quick Key write response is missing config (status={status:#04x}, response={status:02x})"
    ) in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, b""])
async def test_set_quick_key_absent_response_raises(response: bytes | None):
    """Preserve the existing operation error for an absent response."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK_ULTRA)
    with (
        patch.object(device, "_send_command", return_value=response),
        pytest.raises(SwitchbotOperationError, match="Sending command failed"),
    ):
        await device.set_quick_key(enabled=True)
