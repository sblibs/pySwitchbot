"""Test keypad series device functionality using standard pytest."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from switchbot import SwitchbotModel
from switchbot.adv_parser import parse_advertisement_data
from switchbot.devices.device import SwitchbotEncryptedDevice, SwitchbotOperationError
from switchbot.devices.keypad import (
    COMMAND_GET_PASSWORD_COUNT,
    SwitchbotKeypad,
)

from . import KEYPAD_INFO
from .test_adv_parser import generate_advertisement_data, generate_ble_device


@pytest.fixture
def device() -> SwitchbotKeypad:
    """Fixture to create a SwitchbotKeypad device with mocked BLE command methods."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    dev = SwitchbotKeypad(
        ble_device,
        "ff",
        "ffffffffffffffffffffffffffffffff",
        model=SwitchbotModel.KEYPAD,
    )
    dev._send_command = AsyncMock()
    dev._send_command_sequence = AsyncMock()
    dev.update = AsyncMock()
    return dev


@pytest.mark.asyncio
async def test_get_basic_info(device: SwitchbotKeypad) -> None:
    """Test getting basic info from Keypad device."""
    device._get_basic_info = AsyncMock(return_value=b"\x01_\x18\x01")

    info = await device.get_basic_info()
    assert info is not None
    assert info["battery"] == 95
    assert info["firmware"] == 2.4
    assert info["hardware"] == 1


@pytest.mark.asyncio
async def test_get_basic_info_none(device: SwitchbotKeypad) -> None:
    """Test getting basic info returns None when no response."""
    device._get_basic_info = AsyncMock(return_value=None)

    info = await device.get_basic_info()
    assert info is None


@pytest.mark.asyncio
async def test_get_basic_info_truncated(device: SwitchbotKeypad) -> None:
    """Test getting basic info returns None when response is truncated."""
    device._get_basic_info = AsyncMock(return_value=b"\x01_")

    info = await device.get_basic_info()
    assert info is None


@pytest.mark.asyncio
async def test_add_invalid_password(device: SwitchbotKeypad) -> None:
    """Test adding an invalid password raises ValueError."""
    invalid_passwords = ["123", "abcdef", "1234567890123", "12 3456", "passw0rd!"]

    for password in invalid_passwords:
        with pytest.raises(ValueError, match=r"Password must be 6-12 digits\."):
            await device.add_password(password)


@pytest.mark.asyncio
async def test_add_password_invalid_type(device: SwitchbotKeypad) -> None:
    """Test adding a password with out-of-range passcode type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid passcode_type"):
        await device.add_password("123456", passcode_type=4)


@pytest.mark.asyncio
async def test_add_password_invalid_timestamps(device: SwitchbotKeypad) -> None:
    """Test adding a password with invalid start or end time raises ValueError."""
    with pytest.raises(ValueError, match="Invalid start_time"):
        await device.add_password("123456", start_time=-1)

    with pytest.raises(ValueError, match="Invalid end_time"):
        await device.add_password("123456", end_time=0x100000000)


@pytest.mark.asyncio
async def test_add_password_invalid_region(device: SwitchbotKeypad) -> None:
    """Test adding a password with invalid region raises ValueError."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    with pytest.raises(ValueError, match="Invalid region"):
        await device.add_password(
            "123456",
            session=session,
            token="fake-jwt",  # noqa: S106
            region="invalid-region-name-too-long",
        )


@pytest.mark.asyncio
async def test_add_password_success(device: SwitchbotKeypad) -> None:
    """Test adding a valid permanent password successfully sends correct commands."""
    device._send_command.side_effect = [
        b"\x01\x10\x05",
        b"\x01",
    ]

    index = await device.add_password("123456")
    assert index == 5

    assert device._send_command.call_count == 2
    device._send_command.assert_any_call("570F52020210FF0006010203040506")
    device._send_command.assert_any_call("570F520203050000000000000000")


@pytest.mark.asyncio
async def test_add_password_time_limited_success(device: SwitchbotKeypad) -> None:
    """Test adding a valid time-limited password successfully sends time window."""
    device._send_command.side_effect = [
        b"\x01",
        b"\x01\x10\x09",
        b"\x01",
    ]

    index = await device.add_password(
        "987654321",
        passcode_type=1,
        start_time=1700000000,
        end_time=1800000000,
    )
    assert index == 9

    assert device._send_command.call_count == 3
    device._send_command.assert_any_call("570F52020220FF01090908070605040302")
    device._send_command.assert_any_call("570F5202022101")
    device._send_command.assert_any_call("570F520203096553F1006B49D200")


@pytest.mark.asyncio
async def test_add_password_ble_failure(device: SwitchbotKeypad) -> None:
    """Test that BLE failure when adding passcode raises SwitchbotOperationError."""
    device._send_command.return_value = b"\x00"

    with pytest.raises(SwitchbotOperationError, match=r"Failed to add password"):
        await device.add_password("123456")


@pytest.mark.asyncio
async def test_add_password_response_too_short(device: SwitchbotKeypad) -> None:
    """Test that too short response when adding passcode raises SwitchbotOperationError."""
    device._send_command.return_value = b"\x01"

    with pytest.raises(
        SwitchbotOperationError, match=r"Failed to retrieve passcode index"
    ):
        await device.add_password("123456")


@pytest.mark.asyncio
async def test_add_password_time_window_failure(device: SwitchbotKeypad) -> None:
    """Test that failure to set time window triggers rollback delete and raises SwitchbotOperationError."""
    device._send_command.side_effect = [
        b"\x01\x10\x05",  # add response, returns index 5
        b"\x00",  # set time window response (failure)
        b"\x01",  # delete passcode response during rollback
    ]

    with pytest.raises(
        SwitchbotOperationError, match=r"Failed to set active time window"
    ):
        await device.add_password("123456")

    device._send_command.assert_any_call("570F52020505")


@pytest.mark.asyncio
async def test_add_password_time_window_failure_rollback_failure(
    device: SwitchbotKeypad,
) -> None:
    """Test that rollback failure when setting time window fails is handled gracefully and still raises."""
    device._send_command.side_effect = [
        b"\x01\x10\x05",  # add response, returns index 5
        b"\x00",  # set time window response (failure)
        b"\x00",  # delete passcode response fails during rollback
    ]

    with pytest.raises(
        SwitchbotOperationError,
        match=r"Failed to set active time window for passcode\. Rollback failed: passcode at index 5 may still be active on the device\.",
    ):
        await device.add_password("123456")

    device._send_command.assert_any_call("570F52020505")


@pytest.mark.asyncio
async def test_modify_password_invalid_params(device: SwitchbotKeypad) -> None:
    """Test modifying a password with invalid params raises ValueError."""
    with pytest.raises(ValueError, match="Invalid passcode_type"):
        await device.modify_password(3, "654321", passcode_type=9)

    with pytest.raises(ValueError, match="Invalid start_time"):
        await device.modify_password(3, "654321", start_time=-5)

    with pytest.raises(ValueError, match="Invalid end_time"):
        await device.modify_password(3, "654321", end_time=0xFFFFFFFF + 1)


@pytest.mark.asyncio
async def test_modify_password_success(device: SwitchbotKeypad) -> None:
    """Test modifying a password sends correct modify and time commands."""
    device._send_command.side_effect = [
        b"\x01",
        b"\x01",
    ]

    await device.modify_password(
        index=3,
        password="654321",  # noqa: S106
        passcode_type=0,
    )

    assert device._send_command.call_count == 2
    device._send_command.assert_any_call("570F52020210030006060504030201")
    device._send_command.assert_any_call("570F520203030000000000000000")


@pytest.mark.asyncio
async def test_modify_password_failure(device: SwitchbotKeypad) -> None:
    """Test modifying a password raises SwitchbotOperationError and attempts rollback delete on BLE write failure."""
    device._send_command.side_effect = [
        b"\x00",  # BLE modify failed
        b"\x01",  # Rollback delete success
    ]

    with pytest.raises(SwitchbotOperationError, match=r"Failed to modify password"):
        await device.modify_password(
            index=3,
            password="654321",  # noqa: S106
            passcode_type=0,
        )

    device._send_command.assert_any_call("570F52020503")


@pytest.mark.asyncio
async def test_modify_password_time_window_failure(device: SwitchbotKeypad) -> None:
    """Test modifying a password raises SwitchbotOperationError and attempts rollback delete on time window write failure."""
    device._send_command.side_effect = [
        b"\x01",  # modify success
        b"\x00",  # set time window failure
        b"\x01",  # Rollback delete success
    ]

    with pytest.raises(
        SwitchbotOperationError, match=r"Failed to set active time window"
    ):
        await device.modify_password(
            index=3,
            password="654321",  # noqa: S106
            passcode_type=0,
        )

    device._send_command.assert_any_call("570F52020503")


@pytest.mark.asyncio
async def test_modify_password_failure_rollback_failure(
    device: SwitchbotKeypad,
) -> None:
    """Test that modify password raises escalated exception when rollback delete also fails."""
    device._send_command.side_effect = [
        b"\x00",  # BLE modify failed
        b"\x00",  # Rollback delete fails
    ]

    with pytest.raises(
        SwitchbotOperationError,
        match=r"Failed to modify password for index 3\. Rollback failed: passcode at index 3 may still be active on the device or in an indeterminate state\.",
    ):
        await device.modify_password(
            index=3,
            password="654321",  # noqa: S106
            passcode_type=0,
        )

    device._send_command.assert_any_call("570F52020503")


@pytest.mark.asyncio
async def test_delete_password_success(device: SwitchbotKeypad) -> None:
    """Test deleting a password sends correct delete command."""
    device._send_command.return_value = b"\x01"

    result = await device.delete_password(index=4)
    assert result

    device._send_command.assert_awaited_once_with("570F52020504")


@pytest.mark.asyncio
async def test_get_password_count(device: SwitchbotKeypad) -> None:
    """Test getting password counts parses successfully."""
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
async def test_get_password_count_none(device: SwitchbotKeypad) -> None:
    """Test getting password counts returns None on BLE failure."""
    device._send_command.return_value = None

    result = await device.get_password_count()
    assert result is None


@pytest.mark.asyncio
async def test_get_password_count_truncated(device: SwitchbotKeypad) -> None:
    """Test getting password counts returns None on truncated response."""
    device._send_command.return_value = bytes([0x01, 0x03, 0x02])

    result = await device.get_password_count()
    assert result is None


@pytest.mark.asyncio
async def test_sync_time_success(device: SwitchbotKeypad) -> None:
    """Test synchronizing device time sends correct commands."""
    device._send_command.return_value = b"\x01"

    result = await device.sync_time(timestamp=1700000000)
    assert result
    device._send_command.assert_awaited_once_with("570005010000018BCFE56800")


@pytest.mark.asyncio
async def test_sync_time_none_timestamp(device: SwitchbotKeypad) -> None:
    """Test synchronizing device time with system clock when timestamp is None."""
    device._send_command.return_value = b"\x01"

    result = await device.sync_time(timestamp=None)
    assert result
    device._send_command.assert_called_once()
    cmd_sent = device._send_command.call_args[0][0]
    assert cmd_sent.startswith("57000501")
    assert len(cmd_sent) == 24  # 8 char header + 16 char hex timestamp


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify: AsyncMock) -> None:
    """Test verify_encryption_key triggers base check."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await SwitchbotKeypad.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        SwitchbotModel.KEYPAD,
    )
    assert result


@pytest.mark.asyncio
@patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
async def test_add_password_with_cloud_sync(
    mock_api_request: MagicMock, device: SwitchbotKeypad
) -> None:
    """Test adding a passcode with cloud sync option."""
    device._send_command.side_effect = [
        b"\x01\x10\x05",
        b"\x01",
    ]

    session = AsyncMock(spec=aiohttp.ClientSession)

    index = await device.add_password(
        "123456",
        session=session,
        token="fake-jwt-token",  # noqa: S106
        region="us",
        name="Test Passcode",
        creator="UnitTester",
    )
    assert index == 5

    assert device._send_command.call_count == 2
    mock_api_request.assert_awaited_once()

    args, _kwargs = mock_api_request.call_args
    assert args[0] == session
    assert args[1] == "wonderlabs.us"
    assert args[2] == "command/cmd/api/v1/func/invoke"

    payload = args[3]
    assert payload["deviceID"] == "AABBCCDDEEFF"
    assert payload["functionID"] == 4245
    assert payload["params"]["0"] == 5
    assert payload["params"]["5"] == "Test Passcode"
    assert payload["params"]["6"] == "123456"
    assert payload["params"]["7"] == "UnitTester"

    headers = args[4]
    assert headers["authorization"] == "fake-jwt-token"


@pytest.mark.asyncio
async def test_add_password_partial_credentials(device: SwitchbotKeypad) -> None:
    """Test that passing partial credentials for cloud sync raises ValueError."""
    session = AsyncMock(spec=aiohttp.ClientSession)

    with pytest.raises(
        ValueError,
        match=r"To synchronize with SwitchBot Cloud, 'session', 'token', and 'region' must all be provided\.",
    ):
        await device.add_password(
            "123456",
            session=session,
            token="fake-jwt-token",  # noqa: S106
            # region is missing!
        )


@pytest.mark.asyncio
@patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
async def test_add_password_cloud_sync_failure_rollback(
    mock_api_request: MagicMock, device: SwitchbotKeypad
) -> None:
    """Test that cloud sync failure triggers rollback (deletes passcode from device)."""
    device._send_command.side_effect = [
        b"\x01\x10\x05",  # add response, returns index 5
        b"\x01",  # set time window response
        b"\x01",  # delete passcode response during rollback
    ]

    session = AsyncMock(spec=aiohttp.ClientSession)
    mock_api_request.side_effect = Exception("Cloud connection error")

    with pytest.raises(Exception, match="Cloud connection error"):
        await device.add_password(
            "123456",
            session=session,
            token="fake-jwt-token",  # noqa: S106
            region="us",
        )

    # Verify that delete_password was called with index 5
    device._send_command.assert_any_call("570F52020505")


@pytest.mark.asyncio
@patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
async def test_add_password_cloud_sync_failure_and_rollback_failure(
    mock_api_request: MagicMock, device: SwitchbotKeypad
) -> None:
    """Test that when cloud sync fails and the deletion rollback also fails, escalated exception is raised."""
    device._send_command.side_effect = [
        b"\x01\x10\x05",  # add response, returns index 5
        b"\x01",  # set time window response
        b"\x00",  # delete passcode response fails during rollback
    ]

    session = AsyncMock(spec=aiohttp.ClientSession)
    mock_api_request.side_effect = Exception("Cloud connection error")

    with pytest.raises(
        SwitchbotOperationError,
        match=r"SwitchBot Cloud sync failed for passcode at index 5\. Rollback failed: passcode at index 5 may still be active on the device\.",
    ):
        await device.add_password(
            "123456",
            session=session,
            token="fake-jwt-token",  # noqa: S106
            region="us",
        )


def test_keypad_advertisement_battery() -> None:
    """Test that battery is parsed from keypad advertisement data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: KEYPAD_INFO.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": KEYPAD_INFO.service_data},
        rssi=-80,
    )
    advertisement = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.KEYPAD
    )
    device = SwitchbotKeypad(ble_device, "ff", "ffffffffffffffffffffffffffffffff")
    device.update_from_advertisement(advertisement)

    assert device.get_battery_percent() == 100


def test_keypad_advertisement_attempt_state() -> None:
    """Test that attempt_state is parsed from keypad advertisement data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: KEYPAD_INFO.manufacturer_data},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": KEYPAD_INFO.service_data},
        rssi=-80,
    )
    advertisement = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.KEYPAD
    )
    device = SwitchbotKeypad(ble_device, "ff", "ffffffffffffffffffffffffffffffff")
    device.update_from_advertisement(advertisement)

    assert device.attempt_state == 143


def test_keypad_advertisement_battery_none_when_no_data() -> None:
    """Test that battery is None when advertisement data is missing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": KEYPAD_INFO.service_data},
        rssi=-80,
    )
    advertisement = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.KEYPAD
    )
    device = SwitchbotKeypad(ble_device, "ff", "ffffffffffffffffffffffffffffffff")
    device.update_from_advertisement(advertisement)

    assert device.get_battery_percent() is None
    assert device.attempt_state is None
