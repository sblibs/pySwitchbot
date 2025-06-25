from unittest.mock import AsyncMock, Mock, patch

import pytest

from switchbot import SwitchbotModel
from switchbot.const.lock import LockStatus
from switchbot.devices import lock

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(model: str):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    return lock.SwitchbotLock(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=model
    )


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
    ],
)
def test_lock_init(model: str):
    """Test the initialization of the lock device."""
    device = create_device_for_command_testing(model)
    assert device._model == model


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.AIR_PURIFIER,
    ],
)
def test_lock_init_with_invalid_model(model: str):
    """Test that initializing with an invalid model raises ValueError."""
    with pytest.raises(
        ValueError, match="initializing SwitchbotLock with a non-lock model"
    ):
        create_device_for_command_testing(model)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
    ],
)
async def test_verify_encryption_key(model: str):
    """Test verify_encryption_key method."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    with patch("switchbot.devices.lock.super") as mock_super:
        mock_super().verify_encryption_key = AsyncMock(return_value=True)
        result = await lock.SwitchbotLock.verify_encryption_key(
            ble_device, "key_id", "encryption_key", model
        )
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "command"),
    [
        (SwitchbotModel.LOCK, b"W\x0fN\x01\x01\x10\x80"),
        (SwitchbotModel.LOCK_LITE, b"W\x0fN\x01\x01\x10\x81"),
        (SwitchbotModel.LOCK_PRO, b"W\x0fN\x01\x01\x10\x85"),
        (SwitchbotModel.LOCK_ULTRA, b"W\x0fN\x01\x01\x10\x86"),
    ],
)
async def test_lock(model: str, command: bytes):
    """Test lock method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.UNLOCKED)
    with (
        patch.object(device, "_send_command", return_value=b"\x01\x00"),
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00\x64\x01"),
    ):
        result = await device.lock()
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "command"),
    [
        (SwitchbotModel.LOCK, b"W\x0fN\x01\x01\x10\x80"),
        (SwitchbotModel.LOCK_LITE, b"W\x0fN\x01\x01\x10\x81"),
        (SwitchbotModel.LOCK_PRO, b"W\x0fN\x01\x01\x10\x84"),
        (SwitchbotModel.LOCK_ULTRA, b"W\x0fN\x01\x01\x10\x83"),
    ],
)
async def test_unlock(model: str, command: bytes):
    """Test unlock method."""
    device = create_device_for_command_testing(model)
    device._get_adv_value = Mock(return_value=LockStatus.LOCKED)
    with (
        patch.object(device, "_send_command", return_value=b"\x01\x00"),
        patch.object(device, "_enable_notifications", return_value=True),
        patch.object(device, "_get_basic_info", return_value=b"\x00\x64\x01"),
    ):
        result = await device.unlock()
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
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
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
    ],
)
async def test_get_basic_info(model: str):
    """Test get_basic_info method."""
    device = create_device_for_command_testing(model)
    lock_data = b"\x00\x80\x00\x00\x00\x00\x00\x00"
    basic_data = b"\x00\x64\x01"
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
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
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
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
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


def test_parse_basic_data():
    """Test _parse_basic_data method."""
    device = create_device_for_command_testing(SwitchbotModel.LOCK)
    basic_data = b"\x00\x64\x01"
    result = device._parse_basic_data(basic_data)
    assert result["battery"] == 100
    assert result["firmware"] == 0.1


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
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
    ],
)
async def test_enable_notifications(model: str):
    """Test _enable_notifications method."""
    device = create_device_for_command_testing(model)
    with patch.object(device, "_send_command", return_value=b"\x01\x00"):
        result = await device._enable_notifications()
        assert result is True
        assert device._notifications_enabled is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
    ],
)
async def test_enable_notifications_already_enabled(model: str):
    """Test _enable_notifications when already enabled."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = True
    with patch.object(device, "_send_command") as mock_send:
        result = await device._enable_notifications()
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
    ],
)
def test_notification_handler_not_enabled(model: str):
    """Test _notification_handler when notifications not enabled."""
    device = create_device_for_command_testing(model)
    device._notifications_enabled = False
    data = bytearray(b"\x0f\x00\x00\x00\x80\x00\x00\x00\x00\x00")
    with (
        patch.object(device, "_update_lock_status") as mock_update,
        patch.object(
            device.__class__.__bases__[0], "_notification_handler"
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "status"),
    [
        (SwitchbotModel.LOCK, LockStatus.LOCKED),
        (SwitchbotModel.LOCK_LITE, LockStatus.LOCKING),
        (SwitchbotModel.LOCK_PRO, LockStatus.LOCKED),
        (SwitchbotModel.LOCK_ULTRA, LockStatus.LOCKING),
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
