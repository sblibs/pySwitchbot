"""Test keypad series device functionality using standard unittest."""

import unittest
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


class TestSwitchbotKeypad(unittest.IsolatedAsyncioTestCase):
    """Test suite for SwitchbotKeypad."""

    def setUp(self) -> None:
        self.ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
        self.device = SwitchbotKeypad(
            self.ble_device,
            "ff",
            "ffffffffffffffffffffffffffffffff",
            model=SwitchbotModel.KEYPAD,
        )
        self.device._send_command = AsyncMock()
        self.device._send_command_sequence = AsyncMock()
        self.device.update = AsyncMock()

    async def test_get_basic_info(self) -> None:
        """Test getting basic info from Keypad device."""
        self.device._get_basic_info = AsyncMock(return_value=b"\x01_\x18\x01")

        info = await self.device.get_basic_info()
        assert info is not None
        assert info["battery"] == 95
        assert info["firmware"] == 2.4
        assert info["hardware"] == 1

    async def test_get_basic_info_none(self) -> None:
        """Test getting basic info returns None when no response."""
        self.device._get_basic_info = AsyncMock(return_value=None)

        info = await self.device.get_basic_info()
        assert info is None

    async def test_add_invalid_password(self) -> None:
        """Test adding an invalid password raises ValueError."""
        invalid_passwords = ["123", "abcdef", "1234567890123", "12 3456", "passw0rd!"]

        for password in invalid_passwords:
            with pytest.raises(ValueError, match=r"Password must be 6-12 digits\."):
                await self.device.add_password(password)

    async def test_add_password_success(self) -> None:
        """Test adding a valid permanent password successfully sends correct commands."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",
            b"\x01",
        ]

        index = await self.device.add_password("123456")
        assert index == 5

        assert self.device._send_command.call_count == 2
        self.device._send_command.assert_any_call("570F52020210FF0006010203040506")
        self.device._send_command.assert_any_call("570F520203050000000000000000")

    async def test_add_password_time_limited_success(self) -> None:
        """Test adding a valid time-limited password successfully sends time window."""
        self.device._send_command.side_effect = [
            b"\x01",
            b"\x01\x10\x09",
            b"\x01",
        ]

        index = await self.device.add_password(
            "987654321",
            passcode_type=1,
            start_time=1700000000,
            end_time=1800000000,
        )
        assert index == 9

        assert self.device._send_command.call_count == 3
        self.device._send_command.assert_any_call("570F52020220FF01090908070605040302")
        self.device._send_command.assert_any_call("570F5202022101")
        self.device._send_command.assert_any_call("570F520203096553F1006B49D200")

    async def test_add_password_ble_failure(self) -> None:
        """Test that BLE failure when adding passcode raises SwitchbotOperationError."""
        self.device._send_command.return_value = b"\x00"

        with pytest.raises(SwitchbotOperationError, match=r"Failed to add password"):
            await self.device.add_password("123456")

    async def test_add_password_response_too_short(self) -> None:
        """Test that too short response when adding passcode raises SwitchbotOperationError."""
        self.device._send_command.return_value = b"\x01"

        with pytest.raises(
            SwitchbotOperationError, match=r"Failed to retrieve passcode index"
        ):
            await self.device.add_password("123456")

    async def test_add_password_time_window_failure(self) -> None:
        """Test that failure to set time window raises SwitchbotOperationError."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",  # add response, returns index 5
            b"\x00",  # set time window response (failure)
        ]

        with pytest.raises(
            SwitchbotOperationError, match=r"Failed to set active time window"
        ):
            await self.device.add_password("123456")

    async def test_modify_password_success(self) -> None:
        """Test modifying a password sends correct modify and time commands."""
        self.device._send_command.side_effect = [
            b"\x01",
            b"\x01",
        ]

        result = await self.device.modify_password(
            index=3,
            password="654321",  # noqa: S106
            passcode_type=0,
        )
        assert result

        assert self.device._send_command.call_count == 2
        self.device._send_command.assert_any_call("570F52020210030006060504030201")
        self.device._send_command.assert_any_call("570F520203030000000000000000")

    async def test_modify_password_failure(self) -> None:
        """Test modifying a password returns False on BLE write failure."""
        self.device._send_command.return_value = b"\x00"

        result = await self.device.modify_password(
            index=3,
            password="654321",  # noqa: S106
            passcode_type=0,
        )
        assert not result

    async def test_delete_password_success(self) -> None:
        """Test deleting a password sends correct delete command."""
        self.device._send_command.return_value = b"\x01"

        result = await self.device.delete_password(index=4)
        assert result

        self.device._send_command.assert_awaited_once_with("570F52020504")

    async def test_get_password_count(self) -> None:
        """Test getting password counts parses successfully."""
        self.device._send_command.return_value = bytes(
            [0x01, 0x03, 0x02, 0x01, 0x01, 0x00]
        )

        result = await self.device.get_password_count()
        self.device._send_command.assert_awaited_once_with(COMMAND_GET_PASSWORD_COUNT)

        assert result == {
            "pin": 3,
            "nfc": 2,
            "fingerprint": 1,
            "duress_pin": 1,
            "duress_fingerprint": 0,
        }

    async def test_get_password_count_none(self) -> None:
        """Test getting password counts returns None on BLE failure."""
        self.device._send_command.return_value = None

        result = await self.device.get_password_count()
        assert result is None

    async def test_sync_time_success(self) -> None:
        """Test synchronizing device time sends correct commands."""
        self.device._send_command.return_value = b"\x01"

        result = await self.device.sync_time(timestamp=1700000000)
        assert result
        self.device._send_command.assert_awaited_once_with("570005010000018BCFE56800")

    async def test_sync_time_none_timestamp(self) -> None:
        """Test synchronizing device time with system clock when timestamp is None."""
        self.device._send_command.return_value = b"\x01"

        result = await self.device.sync_time(timestamp=None)
        assert result
        self.device._send_command.assert_called_once()
        cmd_sent = self.device._send_command.call_args[0][0]
        assert cmd_sent.startswith("57000501")
        assert len(cmd_sent) == 24  # 8 char header + 16 char hex timestamp

    @patch.object(
        SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock
    )
    async def test_verify_encryption_key(self, mock_parent_verify: MagicMock) -> None:
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

    @patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
    async def test_add_password_with_cloud_sync(
        self, mock_api_request: MagicMock
    ) -> None:
        """Test adding a passcode with cloud sync option."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",
            b"\x01",
        ]

        session = AsyncMock(spec=aiohttp.ClientSession)

        index = await self.device.add_password(
            "123456",
            session=session,
            token="fake-jwt-token",  # noqa: S106
            region="us",
            name="Test Passcode",
            creator="UnitTester",
        )
        assert index == 5

        assert self.device._send_command.call_count == 2
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

    async def test_add_password_partial_credentials(self) -> None:
        """Test that passing partial credentials for cloud sync raises ValueError."""
        session = AsyncMock(spec=aiohttp.ClientSession)

        with pytest.raises(
            ValueError,
            match=r"To synchronize with SwitchBot Cloud, 'session', 'token', and 'region' must all be provided\.",
        ):
            await self.device.add_password(
                "123456",
                session=session,
                token="fake-jwt-token",  # noqa: S106
                # region is missing!
            )

    @patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
    async def test_add_password_cloud_sync_failure_rollback(
        self, mock_api_request: MagicMock
    ) -> None:
        """Test that cloud sync failure triggers rollback (deletes passcode from device)."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",  # add response, returns index 5
            b"\x01",  # set time window response
            b"\x01",  # delete passcode response during rollback
        ]

        session = AsyncMock(spec=aiohttp.ClientSession)
        mock_api_request.side_effect = Exception("Cloud connection error")

        with pytest.raises(Exception, match="Cloud connection error"):
            await self.device.add_password(
                "123456",
                session=session,
                token="fake-jwt-token",  # noqa: S106
                region="us",
            )

        # Verify that delete_password was called with index 5
        self.device._send_command.assert_any_call("570F52020505")

    @patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
    async def test_add_password_cloud_sync_failure_and_rollback_failure(
        self, mock_api_request: MagicMock
    ) -> None:
        """Test that when cloud sync fails and the deletion rollback also fails, exception propagates."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",  # add response, returns index 5
            b"\x01",  # set time window response
            b"\x00",  # delete passcode response fails during rollback
        ]

        session = AsyncMock(spec=aiohttp.ClientSession)
        mock_api_request.side_effect = Exception("Cloud connection error")

        with pytest.raises(Exception, match="Cloud connection error"):
            await self.device.add_password(
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


if __name__ == "__main__":
    unittest.main()
