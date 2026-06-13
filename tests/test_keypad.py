"""Test keypad series device functionality using standard unittest."""

from unittest.mock import AsyncMock, patch
import unittest
from typing import Any

from bleak.backends.device import BLEDevice

from switchbot import SwitchbotModel
from switchbot.devices.device import SwitchbotEncryptedDevice
from switchbot.devices.keypad import (
    COMMAND_GET_PASSWORD_COUNT,
    SwitchbotKeypad,
)
from .test_adv_parser import generate_ble_device


class TestSwitchbotKeypad(unittest.IsolatedAsyncioTestCase):
    """Test suite for SwitchbotKeypad."""

    def setUp(self) -> None:
        self.ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
        self.device = SwitchbotKeypad(
            self.ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=SwitchbotModel.KEYPAD
        )
        self.device._send_command = AsyncMock()
        self.device._send_command_sequence = AsyncMock()
        self.device.update = AsyncMock()

    async def test_get_basic_info(self) -> None:
        """Test getting basic info from Keypad device."""
        self.device._get_basic_info = AsyncMock(return_value=b"\x01_\x18\x01")

        info = await self.device.get_basic_info()
        self.assertIsNotNone(info)
        self.assertEqual(info["battery"], 95)
        self.assertEqual(info["firmware"], 2.4)
        self.assertEqual(info["hardware"], 1)

    async def test_get_basic_info_none(self) -> None:
        """Test getting basic info returns None when no response."""
        self.device._get_basic_info = AsyncMock(return_value=None)

        info = await self.device.get_basic_info()
        self.assertIsNone(info)

    async def test_add_invalid_password(self) -> None:
        """Test adding an invalid password raises ValueError."""
        invalid_passwords = ["123", "abcdef", "1234567890123", "12 3456", "passw0rd!"]

        for password in invalid_passwords:
            with self.assertRaisesRegex(ValueError, "Password must be 6-12 digits."):
                await self.device.add_password(password)

    async def test_add_password_success(self) -> None:
        """Test adding a valid permanent password successfully sends correct commands."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",
            b"\x01",
        ]

        index = await self.device.add_password("123456")
        self.assertEqual(index, 5)

        self.assertEqual(self.device._send_command.call_count, 2)
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
            type=1,
            start_time=1700000000,
            end_time=1800000000,
        )
        self.assertEqual(index, 9)

        self.assertEqual(self.device._send_command.call_count, 3)
        self.device._send_command.assert_any_call("570F52020220FF01090908070605040302")
        self.device._send_command.assert_any_call("570F5202022101")
        self.device._send_command.assert_any_call("570F520203096553F1006B49D200")

    async def test_modify_password_success(self) -> None:
        """Test modifying a password sends correct modify and time commands."""
        self.device._send_command.side_effect = [
            b"\x01",
            b"\x01",
        ]

        result = await self.device.modify_password(
            index=3,
            password="654321",
            type=0,
        )
        self.assertTrue(result)

        self.assertEqual(self.device._send_command.call_count, 2)
        self.device._send_command.assert_any_call("570F52020210030006060504030201")
        self.device._send_command.assert_any_call("570F520203030000000000000000")

    async def test_delete_password_success(self) -> None:
        """Test deleting a password sends correct delete command."""
        self.device._send_command.return_value = b"\x01"

        result = await self.device.delete_password(index=4)
        self.assertTrue(result)

        self.device._send_command.assert_awaited_once_with("570F52020504")

    async def test_get_password_count(self) -> None:
        """Test getting password counts parses successfully."""
        self.device._send_command.return_value = bytes([0x01, 0x03, 0x02, 0x01, 0x01, 0x00])

        result = await self.device.get_password_count()
        self.device._send_command.assert_awaited_once_with(COMMAND_GET_PASSWORD_COUNT)

        self.assertEqual(result, {
            "pin": 3,
            "nfc": 2,
            "fingerprint": 1,
            "duress_pin": 1,
            "duress_fingerprint": 0,
        })



    async def test_sync_time_success(self) -> None:
        """Test synchronizing device time sends correct commands."""
        self.device._send_command.return_value = b"\x01"
        
        result = await self.device.sync_time(timestamp=1700000000)
        self.assertTrue(result)
        self.device._send_command.assert_awaited_once_with("570005010000018BCFE56800")

    @patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
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
        self.assertTrue(result)

    @patch.object(SwitchbotKeypad, "api_request", new_callable=AsyncMock)
    async def test_add_password_with_cloud_sync(self, mock_api_request: MagicMock) -> None:
        """Test adding a passcode with cloud sync option."""
        self.device._send_command.side_effect = [
            b"\x01\x10\x05",
            b"\x01",
        ]

        import aiohttp
        session = AsyncMock(spec=aiohttp.ClientSession)
        
        index = await self.device.add_password(
            "123456",
            session=session,
            token="fake-jwt-token",
            region="us",
            name="Test Passcode",
            creator="UnitTester"
        )
        self.assertEqual(index, 5)

        self.assertEqual(self.device._send_command.call_count, 2)
        mock_api_request.assert_awaited_once()
        
        args, kwargs = mock_api_request.call_args
        self.assertEqual(args[0], session)
        self.assertEqual(args[1], "wonderlabs.us")
        self.assertEqual(args[2], "command/cmd/api/v1/func/invoke")
        
        payload = args[3]
        self.assertEqual(payload["deviceID"], "AABBCCDDEEFF")
        self.assertEqual(payload["functionID"], 4245)
        self.assertEqual(payload["params"]["0"], 5)
        self.assertEqual(payload["params"]["5"], "Test Passcode")
        self.assertEqual(payload["params"]["6"], "123456")
        self.assertEqual(payload["params"]["7"], "UnitTester")
        
        headers = args[4]
        self.assertEqual(headers["authorization"], "fake-jwt-token")


if __name__ == "__main__":
    unittest.main()
