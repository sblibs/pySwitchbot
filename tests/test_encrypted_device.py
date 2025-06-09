"""Tests for SwitchbotEncryptedDevice base class."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from bleak.exc import BleakDBusError

from switchbot import SwitchbotModel
from switchbot.devices.device import (
    SwitchbotEncryptedDevice,
)

from .test_adv_parser import generate_ble_device


class MockEncryptedDevice(SwitchbotEncryptedDevice):
    """Mock encrypted device for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update_count: int = 0

    async def update(self, interface: int | None = None) -> None:
        self.update_count += 1


def create_encrypted_device(
    model: SwitchbotModel = SwitchbotModel.LOCK,
) -> MockEncryptedDevice:
    """Create an encrypted device for testing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Test Device")
    return MockEncryptedDevice(
        ble_device, "01", "0123456789abcdef0123456789abcdef", model=model
    )


@pytest.mark.asyncio
async def test_encrypted_device_init() -> None:
    """Test encrypted device initialization."""
    device = create_encrypted_device()
    assert device._key_id == "01"
    assert device._encryption_key == bytearray.fromhex(
        "0123456789abcdef0123456789abcdef"
    )
    assert device._iv is None
    assert device._cipher is None


@pytest.mark.asyncio
async def test_encrypted_device_init_validation() -> None:
    """Test encrypted device initialization with invalid parameters."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "Test Device")

    # Test empty key_id
    with pytest.raises(ValueError, match="key_id is missing"):
        MockEncryptedDevice(
            ble_device, "", "0123456789abcdef0123456789abcdef", SwitchbotModel.LOCK
        )

    # Test invalid key_id length
    with pytest.raises(ValueError, match="key_id is invalid"):
        MockEncryptedDevice(
            ble_device, "1", "0123456789abcdef0123456789abcdef", SwitchbotModel.LOCK
        )

    # Test empty encryption_key
    with pytest.raises(ValueError, match="encryption_key is missing"):
        MockEncryptedDevice(ble_device, "01", "", SwitchbotModel.LOCK)

    # Test invalid encryption_key length
    with pytest.raises(ValueError, match="encryption_key is invalid"):
        MockEncryptedDevice(ble_device, "01", "0123456789abcdef", SwitchbotModel.LOCK)


@pytest.mark.asyncio
async def test_send_command_unencrypted() -> None:
    """Test sending unencrypted command."""
    device = create_encrypted_device()

    with patch.object(device, "_send_command_locked_with_retry") as mock_send:
        mock_send.return_value = b"\x01\x00\x00\x00"

        result = await device._send_command("570200", encrypt=False)

        assert result == b"\x01\x00\x00\x00"
        mock_send.assert_called_once()
        # Verify the key was padded with zeros for unencrypted command
        call_args = mock_send.call_args[0]
        assert call_args[0] == "570000000200"  # Original key with zeros inserted


@pytest.mark.asyncio
async def test_send_command_encrypted_success() -> None:
    """Test successful encrypted command."""
    device = create_encrypted_device()

    # Mock the connection and command execution
    with (
        patch.object(device, "_send_command_locked_with_retry") as mock_send,
        patch.object(device, "_decrypt") as mock_decrypt,
    ):
        mock_decrypt.return_value = b"decrypted_response"

        # First call is for IV initialization, second is for the actual command
        mock_send.side_effect = [
            b"\x01\x00\x00\x00\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0",  # IV response (16 bytes)
            b"\x01\x00\x00\x00encrypted_response",  # Command response
        ]

        result = await device._send_command("570200", encrypt=True)

        assert result is not None
        assert mock_send.call_count == 2
        # Verify IV was initialized
        assert device._iv is not None


@pytest.mark.asyncio
async def test_send_command_iv_already_initialized() -> None:
    """Test sending encrypted command when IV is already initialized."""
    device = create_encrypted_device()

    # Pre-set the IV
    device._iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0"

    with (
        patch.object(device, "_send_command_locked_with_retry") as mock_send,
        patch.object(device, "_encrypt") as mock_encrypt,
        patch.object(device, "_decrypt") as mock_decrypt,
    ):
        mock_encrypt.return_value = (
            "656e637279707465645f64617461"  # "encrypted_data" in hex
        )
        mock_decrypt.return_value = b"decrypted_response"
        mock_send.return_value = b"\x01\x00\x00\x00encrypted_response"

        result = await device._send_command("570200", encrypt=True)

        assert result == b"\x01decrypted_response"
        # Should only call once since IV is already initialized
        mock_send.assert_called_once()
        mock_encrypt.assert_called_once()
        mock_decrypt.assert_called_once()


@pytest.mark.asyncio
async def test_iv_race_condition_during_disconnect() -> None:
    """Test that commands during disconnect are handled properly."""
    device = create_encrypted_device()

    # Pre-set the IV
    device._iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78"

    # Mock the connection
    mock_client = AsyncMock()
    mock_client.is_connected = True
    device._client = mock_client

    async def simulate_disconnect() -> None:
        """Simulate disconnect happening during command execution."""
        await asyncio.sleep(0.01)  # Small delay
        await device._execute_disconnect()

    with (
        patch.object(device, "_send_command_locked_with_retry") as mock_send,
        patch.object(device, "_ensure_connected"),
        patch.object(device, "_encrypt") as mock_encrypt,
        patch.object(device, "_decrypt") as mock_decrypt,
    ):
        mock_encrypt.return_value = "656e63727970746564"  # "encrypted" in hex
        mock_decrypt.return_value = b"response"
        mock_send.return_value = b"\x01\x00\x00\x00response"

        # Start command and disconnect concurrently
        command_task = asyncio.create_task(device._send_command("570200"))
        disconnect_task = asyncio.create_task(simulate_disconnect())

        # Both should complete without error
        result, _ = await asyncio.gather(
            command_task, disconnect_task, return_exceptions=True
        )

        # Command should have completed successfully
        assert isinstance(result, bytes) or result is None
        # IV should be cleared after disconnect
        assert device._iv is None


@pytest.mark.asyncio
async def test_ensure_encryption_initialized_with_lock_held() -> None:
    """Test that _ensure_encryption_initialized properly handles the operation lock."""
    device = create_encrypted_device()

    # Acquire the operation lock
    async with device._operation_lock:
        with patch.object(device, "_send_command_locked_with_retry") as mock_send:
            mock_send.return_value = b"\x01\x00\x00\x00\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0"

            result = await device._ensure_encryption_initialized()

            assert result is True
            assert (
                device._iv
                == b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0"
            )
            assert device._cipher is None  # Should be reset when IV changes


@pytest.mark.asyncio
async def test_ensure_encryption_initialized_failure() -> None:
    """Test _ensure_encryption_initialized when IV initialization fails."""
    device = create_encrypted_device()

    async with device._operation_lock:
        with patch.object(device, "_send_command_locked_with_retry") as mock_send:
            # Return failure response
            mock_send.return_value = b"\x00"

            result = await device._ensure_encryption_initialized()

            assert result is False
            assert device._iv is None


@pytest.mark.asyncio
async def test_encrypt_decrypt_with_valid_iv() -> None:
    """Test encryption and decryption with valid IV."""
    device = create_encrypted_device()
    device._iv = b"\x00" * 16  # Use zeros for predictable test

    # Test encryption
    encrypted = device._encrypt("48656c6c6f")  # "Hello" in hex
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0

    # Test decryption
    decrypted = device._decrypt(bytearray.fromhex(encrypted))
    assert decrypted.hex() == "48656c6c6f"


@pytest.mark.asyncio
async def test_encrypt_with_none_iv() -> None:
    """Test that encryption raises error when IV is None."""
    device = create_encrypted_device()
    device._iv = None

    with pytest.raises(RuntimeError, match="Cannot encrypt: IV is None"):
        device._encrypt("48656c6c6f")


@pytest.mark.asyncio
async def test_decrypt_with_none_iv() -> None:
    """Test that decryption raises error when IV is None."""
    device = create_encrypted_device()
    device._iv = None

    with pytest.raises(RuntimeError, match="Cannot decrypt: IV is None"):
        device._decrypt(bytearray.fromhex("48656c6c6f"))


@pytest.mark.asyncio
async def test_get_cipher_with_none_iv() -> None:
    """Test that _get_cipher raises error when IV is None."""
    device = create_encrypted_device()
    device._iv = None

    with pytest.raises(RuntimeError, match="Cannot create cipher: IV is None"):
        device._get_cipher()


@pytest.mark.asyncio
async def test_execute_disconnect_clears_encryption_state() -> None:
    """Test that disconnect properly clears encryption state."""
    device = create_encrypted_device()
    device._iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0"
    device._cipher = None  # type: ignore[assignment]

    # Mock client
    mock_client = AsyncMock()
    device._client = mock_client

    with patch.object(device, "_execute_disconnect_with_lock") as mock_disconnect:
        await device._execute_disconnect()

    assert device._iv is None
    assert device._cipher is None
    mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_commands_with_same_device() -> None:
    """Test multiple concurrent commands on the same device."""
    device = create_encrypted_device()

    # Pre-initialize IV (16 bytes for AES CTR mode)
    device._iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0"

    with (
        patch.object(device, "_send_command_locked_with_retry") as mock_send,
        patch.object(device, "_encrypt") as mock_encrypt,
        patch.object(device, "_decrypt") as mock_decrypt,
    ):
        mock_encrypt.return_value = "656e63727970746564"  # "encrypted" in hex
        mock_decrypt.return_value = b"response"
        mock_send.return_value = b"\x01\x00\x00\x00data"

        # Send multiple commands concurrently
        tasks = [
            device._send_command("570200"),
            device._send_command("570201"),
            device._send_command("570202"),
        ]

        results = await asyncio.gather(*tasks)

        # All commands should succeed
        assert all(result == b"\x01response" for result in results)
        assert mock_send.call_count == 3


@pytest.mark.asyncio
async def test_command_retry_with_encryption() -> None:
    """Test command retry logic with encrypted commands."""
    device = create_encrypted_device()
    device._retry_count = 2

    # Pre-initialize IV (16 bytes for AES CTR mode)
    device._iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x56\x78\x9a\xbc\xde\xf0"

    with (
        patch.object(device, "_send_command_locked") as mock_send_locked,
        patch.object(device, "_ensure_connected"),
        patch.object(device, "_encrypt") as mock_encrypt,
        patch.object(device, "_decrypt") as mock_decrypt,
    ):
        mock_encrypt.return_value = "656e63727970746564"  # "encrypted" in hex
        mock_decrypt.return_value = b"response"

        # First attempt fails, second succeeds
        mock_send_locked.side_effect = [
            BleakDBusError("org.bluez.Error", []),
            b"\x01\x00\x00\x00data",
        ]

        result = await device._send_command("570200")

        assert result == b"\x01response"
        assert mock_send_locked.call_count == 2


@pytest.mark.asyncio
async def test_empty_data_encryption_decryption() -> None:
    """Test encryption/decryption of empty data."""
    device = create_encrypted_device()
    device._iv = b"\x00" * 16

    # Test empty encryption
    encrypted = device._encrypt("")
    assert encrypted == ""

    # Test empty decryption
    decrypted = device._decrypt(bytearray())
    assert decrypted == b""
