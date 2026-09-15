"""Tests for device.py functionality."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from switchbot import fetch_cloud_devices, fetch_cloud_devices_by_token
from switchbot.adv_parser import _MODEL_TO_MAC_CACHE, populate_model_to_mac_cache
from switchbot.const import (
    SwitchbotAccountConnectionError,
    SwitchbotApiError,
    SwitchbotAuthenticationError,
    SwitchbotModel,
)
from switchbot.devices.device import (
    SwitchbotBaseDevice,
    SwitchbotDevice,
    SwitchbotEncryptedDevice,
    _extract_region,
    _masked_device_id,
)

from .test_adv_parser import generate_ble_device


@pytest.fixture
def mock_auth_response() -> dict[str, Any]:
    """Mock authentication response."""
    return {
        "access_token": "test_token_123",
        "refresh_token": "refresh_token_123",
        "expires_in": 3600,
    }


@pytest.fixture
def mock_user_info() -> dict[str, Any]:
    """Mock user info response."""
    return {
        "botRegion": "us",
        "country": "us",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_device_response() -> dict[str, Any]:
    """Mock device list response."""
    return {
        "Items": [
            {
                "device_mac": "aabbccddeeff",
                "device_name": "Test Bot",
                "device_detail": {
                    "device_type": "WoHand",
                    "version": "1.0.0",
                },
            },
            {
                "device_mac": "112233445566",
                "device_name": "Test Curtain",
                "device_detail": {
                    "device_type": "WoCurtain",
                    "version": "2.0.0",
                },
            },
            {
                "device_mac": "778899aabbcc",
                "device_name": "Test Lock",
                "device_detail": {
                    "device_type": "WoLock",
                    "version": "1.5.0",
                },
            },
            {
                "device_mac": "ddeeff001122",
                "device_name": "Unknown Device",
                "device_detail": {
                    "device_type": "WoUnknown",
                    "version": "1.0.0",
                    "extra_field": "extra_value",
                },
            },
            {
                "device_mac": "invalid_device",
                # Missing device_detail
            },
            {
                "device_mac": "another_invalid",
                "device_detail": {
                    # Missing device_type
                    "version": "1.0.0",
                },
            },
        ]
    }


@pytest.mark.asyncio
async def test_get_devices(
    mock_auth_response: dict[str, Any],
    mock_user_info: dict[str, Any],
    mock_device_response: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test get_devices method."""
    caplog.set_level(logging.DEBUG)

    with (
        patch.object(
            SwitchbotBaseDevice, "_get_auth_result", return_value=mock_auth_response
        ),
        patch.object(
            SwitchbotBaseDevice, "_async_get_user_info", return_value=mock_user_info
        ),
        patch.object(
            SwitchbotBaseDevice, "api_request", return_value=mock_device_response
        ) as mock_api_request,
        patch(
            "switchbot.devices.device.populate_model_to_mac_cache"
        ) as mock_populate_cache,
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await SwitchbotBaseDevice.get_devices(
            session, "test@example.com", "password123"
        )

        # Check that api_request was called with correct parameters
        mock_api_request.assert_called_once_with(
            session,
            "wonderlabs.us",
            "wonder/device/v3/getdevice",
            {"required_type": "All"},
            {"authorization": "test_token_123"},
        )

        # Check returned dictionary
        assert len(result) == 3  # Only valid devices with known models
        assert result["AA:BB:CC:DD:EE:FF"] == SwitchbotModel.BOT
        assert result["11:22:33:44:55:66"] == SwitchbotModel.CURTAIN
        assert result["77:88:99:AA:BB:CC"] == SwitchbotModel.LOCK

        # Check that cache was populated
        assert mock_populate_cache.call_count == 3
        mock_populate_cache.assert_any_call("AA:BB:CC:DD:EE:FF", SwitchbotModel.BOT)
        mock_populate_cache.assert_any_call("11:22:33:44:55:66", SwitchbotModel.CURTAIN)
        mock_populate_cache.assert_any_call("77:88:99:AA:BB:CC", SwitchbotModel.LOCK)

        # Check that unknown model was logged
        assert "Unknown model WoUnknown for device DD:EE:FF:00:11:22" in caplog.text
        assert "extra_field" in caplog.text
        assert "extra_value" in caplog.text


@pytest.mark.asyncio
async def test_get_devices_with_region(
    mock_auth_response: dict[str, Any],
    mock_device_response: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test get_devices with different region."""
    mock_user_info_eu = {
        "botRegion": "eu",
        "country": "de",
        "email": "test@example.com",
    }

    with (
        patch.object(
            SwitchbotBaseDevice, "_get_auth_result", return_value=mock_auth_response
        ),
        patch.object(
            SwitchbotBaseDevice, "_async_get_user_info", return_value=mock_user_info_eu
        ),
        patch.object(
            SwitchbotBaseDevice, "api_request", return_value=mock_device_response
        ) as mock_api_request,
        patch("switchbot.devices.device.populate_model_to_mac_cache"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        await SwitchbotBaseDevice.get_devices(
            session, "test@example.com", "password123"
        )

        # Check that EU region was used
        mock_api_request.assert_called_once_with(
            session,
            "wonderlabs.eu",
            "wonder/device/v3/getdevice",
            {"required_type": "All"},
            {"authorization": "test_token_123"},
        )


@pytest.mark.asyncio
async def test_get_devices_no_region(
    mock_auth_response: dict[str, Any],
    mock_device_response: dict[str, Any],
) -> None:
    """Test get_devices with no region specified (defaults to us)."""
    mock_user_info_no_region = {
        "email": "test@example.com",
    }

    with (
        patch.object(
            SwitchbotBaseDevice, "_get_auth_result", return_value=mock_auth_response
        ),
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value=mock_user_info_no_region,
        ),
        patch.object(
            SwitchbotBaseDevice, "api_request", return_value=mock_device_response
        ) as mock_api_request,
        patch("switchbot.devices.device.populate_model_to_mac_cache"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        await SwitchbotBaseDevice.get_devices(
            session, "test@example.com", "password123"
        )

        # Check that default US region was used
        mock_api_request.assert_called_once_with(
            session,
            "wonderlabs.us",
            "wonder/device/v3/getdevice",
            {"required_type": "All"},
            {"authorization": "test_token_123"},
        )


@pytest.mark.asyncio
async def test_get_devices_empty_region(
    mock_auth_response: dict[str, Any],
    mock_device_response: dict[str, Any],
) -> None:
    """Test get_devices with empty region string (defaults to us)."""
    mock_user_info_empty_region = {
        "botRegion": "",
        "email": "test@example.com",
    }

    with (
        patch.object(
            SwitchbotBaseDevice, "_get_auth_result", return_value=mock_auth_response
        ),
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value=mock_user_info_empty_region,
        ),
        patch.object(
            SwitchbotBaseDevice, "api_request", return_value=mock_device_response
        ) as mock_api_request,
        patch("switchbot.devices.device.populate_model_to_mac_cache"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        await SwitchbotBaseDevice.get_devices(
            session, "test@example.com", "password123"
        )

        # Check that default US region was used
        mock_api_request.assert_called_once_with(
            session,
            "wonderlabs.us",
            "wonder/device/v3/getdevice",
            {"required_type": "All"},
            {"authorization": "test_token_123"},
        )


@pytest.mark.asyncio
async def test_fetch_cloud_devices(
    mock_auth_response: dict[str, Any],
    mock_user_info: dict[str, Any],
    mock_device_response: dict[str, Any],
) -> None:
    """Test fetch_cloud_devices wrapper function."""
    with (
        patch.object(
            SwitchbotBaseDevice, "_get_auth_result", return_value=mock_auth_response
        ),
        patch.object(
            SwitchbotBaseDevice, "_async_get_user_info", return_value=mock_user_info
        ),
        patch.object(
            SwitchbotBaseDevice, "api_request", return_value=mock_device_response
        ),
        patch(
            "switchbot.devices.device.populate_model_to_mac_cache"
        ) as mock_populate_cache,
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await fetch_cloud_devices(session, "test@example.com", "password123")

        # Check returned dictionary
        assert len(result) == 3
        assert result["AA:BB:CC:DD:EE:FF"] == SwitchbotModel.BOT
        assert result["11:22:33:44:55:66"] == SwitchbotModel.CURTAIN
        assert result["77:88:99:AA:BB:CC"] == SwitchbotModel.LOCK

        # Check that cache was populated
        assert mock_populate_cache.call_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("region", ["us", "eu", "jp"])
async def test_fetch_cloud_devices_by_token(
    mock_user_info: dict[str, Any],
    mock_device_response: dict[str, Any],
    region: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test fetching cloud devices with an OAuth access token."""
    caplog.set_level(logging.DEBUG, logger="switchbot.devices.device")
    with (
        patch.object(SwitchbotBaseDevice, "_get_auth_result") as mock_get_auth_result,
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value={**mock_user_info, "botRegion": region},
        ) as mock_get_user_info,
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            return_value=mock_device_response,
        ) as mock_api_request,
        patch(
            "switchbot.devices.device.populate_model_to_mac_cache"
        ) as mock_populate_cache,
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await fetch_cloud_devices_by_token(session, "oauth-access-token")

    mock_get_auth_result.assert_not_called()
    mock_get_user_info.assert_awaited_once_with(
        session, {"authorization": "oauth-access-token"}
    )
    mock_api_request.assert_awaited_once_with(
        session,
        f"wonderlabs.{region}",
        "wonder/device/v3/getdevice",
        {"required_type": "All"},
        {"authorization": "oauth-access-token"},
    )
    assert result["AA:BB:CC:DD:EE:FF"] == SwitchbotModel.BOT
    assert mock_populate_cache.call_count == 3
    assert "retrieval finished; supported_devices=3 duration_ms=" in caplog.text
    assert f"region resolved to {region}" in caplog.text
    assert "oauth-access-token" not in caplog.text


@pytest.mark.asyncio
async def test_fetch_cloud_devices_by_token_connection_error(
    mock_user_info: dict[str, Any],
) -> None:
    """Test an API error while fetching cloud devices with an OAuth token."""
    with (
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            side_effect=Exception("Network error"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(
            SwitchbotAccountConnectionError, match="Failed to retrieve devices"
        ):
            await fetch_cloud_devices_by_token(session, "oauth-access-token")


@pytest.mark.asyncio
async def test_fetch_cloud_devices_by_token_authentication_error() -> None:
    """Test an authentication error while fetching devices with an OAuth token."""
    with patch.object(
        SwitchbotBaseDevice,
        "_async_get_user_info",
        side_effect=SwitchbotAuthenticationError("invalid token"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotAuthenticationError, match="invalid token"):
            await fetch_cloud_devices_by_token(session, "oauth-access-token")


@pytest.mark.asyncio
async def test_get_devices_preserves_authentication_error_after_user_info(
    mock_user_info: dict[str, Any],
) -> None:
    """Test device retrieval preserves authentication errors."""
    with (
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            side_effect=SwitchbotAuthenticationError("expired token"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotAuthenticationError, match="expired token"):
            await fetch_cloud_devices_by_token(session, "oauth-access-token")


@pytest.mark.asyncio
async def test_get_devices_preserves_api_error_after_user_info(
    mock_user_info: dict[str, Any],
) -> None:
    """Test device retrieval preserves API errors."""
    with (
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            side_effect=SwitchbotApiError("API error"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotApiError, match="API error"):
            await fetch_cloud_devices_by_token(session, "oauth-access-token")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device_info",
    [
        pytest.param({}, id="missing-items"),
        pytest.param({"Items": None}, id="invalid-items"),
        pytest.param({"Items": {}}, id="items-not-list"),
        pytest.param({"Items": ["invalid"]}, id="invalid-item"),
    ],
)
async def test_get_devices_rejects_invalid_response(
    mock_user_info: dict[str, Any], device_info: dict[str, Any]
) -> None:
    """Test malformed device responses retain their API error classification."""
    with (
        patch.object(
            SwitchbotBaseDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            return_value=device_info,
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotApiError, match="Invalid device response"):
            await fetch_cloud_devices_by_token(session, "oauth-access-token")


@pytest.mark.asyncio
async def test_get_user_info_preserves_authentication_error() -> None:
    """Test user info retrieval preserves authentication errors."""
    with patch.object(
        SwitchbotBaseDevice,
        "api_request",
        side_effect=SwitchbotAuthenticationError("invalid token"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotAuthenticationError, match="invalid token"):
            await SwitchbotBaseDevice._async_get_user_info(
                session,
                {"authorization": "invalid-token"},
            )


@pytest.mark.asyncio
async def test_get_user_info_preserves_api_error() -> None:
    """Test user info retrieval preserves API errors."""
    with patch.object(
        SwitchbotBaseDevice,
        "api_request",
        side_effect=SwitchbotApiError("API error"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotApiError, match="API error"):
            await SwitchbotBaseDevice._async_get_user_info(
                session,
                {"authorization": "invalid-token"},
            )


@pytest.mark.asyncio
async def test_api_request_debug_logs_response_shape_without_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test API debug logs contain response fields but no sensitive values."""
    response = MagicMock()
    response.status = 200
    response.headers = {"x-amzn-requestid": "api-request-id"}
    response.json = AsyncMock(
        return_value={
            "statusCode": 100,
            "message": "success",
            "body": {
                "access_token": "sensitive-access-token",
                "deviceId": "sensitive-device-id",
                "encryptionKey": "sensitive-encryption-key",
            },
        }
    )
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.return_value.__aenter__ = AsyncMock(return_value=response)
    session.post.return_value.__aexit__ = AsyncMock(return_value=None)
    caplog.set_level(logging.DEBUG, logger="switchbot.devices.device")

    result = await SwitchbotBaseDevice.api_request(
        session, "account", "account/api/v1/user/userinfo"
    )

    assert result["deviceId"] == "sensitive-device-id"
    assert "response fields=['body', 'message', 'statusCode']" in caplog.text
    assert "body fields=['access_token', 'deviceId', 'encryptionKey']" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "request_id=api-request-id" in caplog.text
    for sensitive_value in (
        "sensitive-access-token",
        "sensitive-device-id",
        "sensitive-encryption-key",
    ):
        assert sensitive_value not in caplog.text


@pytest.mark.asyncio
async def test_api_request_authentication_error() -> None:
    """Test HTTP authentication errors retain their specific error type."""
    response = MagicMock()
    response.status = 401
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.return_value.__aenter__.return_value = response

    with pytest.raises(SwitchbotAuthenticationError, match="Authentication rejected"):
        await SwitchbotBaseDevice.api_request(
            session,
            "account",
            "account/api/v1/user/userinfo",
            {},
            {"authorization": "invalid-token"},
        )


@pytest.mark.asyncio
async def test_retrieve_encryption_key_with_password() -> None:
    """Test the password flow delegates with its access token."""
    key_details = {
        "key_id": "ff",
        "encryption_key": "ffffffffffffffffffffffffffffffff",
    }
    with (
        patch.object(
            SwitchbotEncryptedDevice,
            "_get_auth_result",
            return_value={"access_token": "password-access-token"},
        ) as mock_get_auth_result,
        patch.object(
            SwitchbotEncryptedDevice,
            "_async_retrieve_encryption_key",
            return_value=key_details,
        ) as mock_retrieve_key,
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await SwitchbotEncryptedDevice.async_retrieve_encryption_key(
            session,
            "aa:bb:cc:dd:ee:ff",
            "test@example.com",
            "password",
        )

    mock_get_auth_result.assert_awaited_once_with(
        session, "test@example.com", "password"
    )
    mock_retrieve_key.assert_awaited_once_with(
        session,
        "aa:bb:cc:dd:ee:ff",
        {"authorization": "password-access-token"},
    )
    assert result == key_details


@pytest.mark.asyncio
async def test_retrieve_encryption_key_by_token_api_error(
    mock_user_info: dict[str, Any],
) -> None:
    """Test an API error while retrieving a key with an OAuth token."""
    with (
        patch.object(
            SwitchbotEncryptedDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotEncryptedDevice,
            "api_request",
            side_effect=SwitchbotApiError("API error"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotApiError, match="API error"):
            await SwitchbotEncryptedDevice.async_retrieve_encryption_key_by_token(
                session, "aa:bb:cc:dd:ee:ff", "oauth-access-token"
            )


@pytest.mark.asyncio
async def test_retrieve_encryption_key_by_token_authentication_error(
    mock_user_info: dict[str, Any],
) -> None:
    """Test key retrieval preserves authentication errors."""
    with (
        patch.object(
            SwitchbotEncryptedDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotEncryptedDevice,
            "api_request",
            side_effect=SwitchbotAuthenticationError("expired token"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotAuthenticationError, match="expired token"):
            await SwitchbotEncryptedDevice.async_retrieve_encryption_key_by_token(
                session, "aa:bb:cc:dd:ee:ff", "oauth-access-token"
            )


@pytest.mark.asyncio
async def test_retrieve_encryption_key_by_token_connection_error(
    mock_user_info: dict[str, Any],
) -> None:
    """Test key retrieval maps unexpected request errors to connection errors."""
    with (
        patch.object(
            SwitchbotEncryptedDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotEncryptedDevice,
            "api_request",
            side_effect=Exception("network error"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(
            SwitchbotAccountConnectionError,
            match="Failed to retrieve encryption key",
        ):
            await SwitchbotEncryptedDevice.async_retrieve_encryption_key_by_token(
                session, "aa:bb:cc:dd:ee:ff", "oauth-access-token"
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device_info",
    [
        pytest.param({}, id="missing-communication-key"),
        pytest.param({"communicationKey": None}, id="invalid-communication-key"),
        pytest.param(
            {"communicationKey": {"key": "encryption-key"}}, id="missing-key-id"
        ),
        pytest.param(
            {"communicationKey": {"keyId": "ff"}}, id="missing-encryption-key"
        ),
        pytest.param(
            {"communicationKey": {"keyId": 1, "key": "encryption-key"}},
            id="invalid-key-id",
        ),
    ],
)
async def test_retrieve_encryption_key_by_token_invalid_response(
    mock_user_info: dict[str, Any], device_info: dict[str, Any]
) -> None:
    """Test malformed key responses retain their API error classification."""
    with (
        patch.object(
            SwitchbotEncryptedDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ),
        patch.object(
            SwitchbotEncryptedDevice,
            "api_request",
            return_value=device_info,
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotApiError, match="Invalid encryption key response"):
            await SwitchbotEncryptedDevice.async_retrieve_encryption_key_by_token(
                session, "aa:bb:cc:dd:ee:ff", "oauth-access-token"
            )


@pytest.mark.asyncio
async def test_retrieve_encryption_key_by_token(
    mock_user_info: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test retrieving an encryption key with an OAuth access token."""
    caplog.set_level(logging.DEBUG, logger="switchbot.devices.device")
    with (
        patch.object(
            SwitchbotEncryptedDevice,
            "_async_get_user_info",
            return_value=mock_user_info,
        ) as mock_get_user_info,
        patch.object(
            SwitchbotEncryptedDevice,
            "api_request",
            return_value={
                "communicationKey": {
                    "keyId": "ff",
                    "key": "ffffffffffffffffffffffffffffffff",
                }
            },
        ) as mock_api_request,
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await SwitchbotEncryptedDevice.async_retrieve_encryption_key_by_token(
            session, "aa:bb:cc:dd:ee:ff", "oauth-access-token"
        )

    auth_headers = {"authorization": "oauth-access-token"}
    mock_get_user_info.assert_awaited_once_with(session, auth_headers)
    mock_api_request.assert_awaited_once_with(
        session,
        "wonderlabs.us",
        "wonder/keys/v1/communicate",
        {"device_mac": "AABBCCDDEEFF", "keyType": "user"},
        auth_headers,
    )
    assert result == {
        "key_id": "ff",
        "encryption_key": "ffffffffffffffffffffffffffffffff",
    }
    assert "device=****EEFF" in caplog.text
    assert "retrieval finished; device=****EEFF duration_ms=" in caplog.text
    for sensitive_value in (
        "aa:bb:cc:dd:ee:ff",
        "oauth-access-token",
        "ffffffffffffffffffffffffffffffff",
    ):
        assert sensitive_value not in caplog.text


@pytest.mark.asyncio
async def test_get_devices_authentication_error() -> None:
    """Test get_devices with authentication error."""
    with patch.object(
        SwitchbotBaseDevice,
        "_get_auth_result",
        side_effect=Exception("Auth failed"),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotAuthenticationError) as exc_info:
            await SwitchbotBaseDevice.get_devices(
                session, "test@example.com", "wrong_password"
            )
        assert "Authentication failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_devices_connection_error(
    mock_auth_response: dict[str, Any],
    mock_user_info: dict[str, Any],
) -> None:
    """Test get_devices with connection error."""
    with (
        patch.object(
            SwitchbotBaseDevice, "_get_auth_result", return_value=mock_auth_response
        ),
        patch.object(
            SwitchbotBaseDevice, "_async_get_user_info", return_value=mock_user_info
        ),
        patch.object(
            SwitchbotBaseDevice,
            "api_request",
            side_effect=Exception("Network error"),
        ),
    ):
        session = MagicMock(spec=aiohttp.ClientSession)
        with pytest.raises(SwitchbotAccountConnectionError) as exc_info:
            await SwitchbotBaseDevice.get_devices(
                session, "test@example.com", "password123"
            )
        assert "Failed to retrieve devices" in str(exc_info.value)


@pytest.mark.asyncio
async def test_populate_model_to_mac_cache() -> None:
    """Test the populate_model_to_mac_cache helper function."""
    # Clear the cache first
    _MODEL_TO_MAC_CACHE.clear()

    # Populate cache with test data
    populate_model_to_mac_cache("AA:BB:CC:DD:EE:FF", SwitchbotModel.BOT)
    populate_model_to_mac_cache("11:22:33:44:55:66", SwitchbotModel.CURTAIN)

    # Check cache contents
    assert _MODEL_TO_MAC_CACHE["AA:BB:CC:DD:EE:FF"] == SwitchbotModel.BOT
    assert _MODEL_TO_MAC_CACHE["11:22:33:44:55:66"] == SwitchbotModel.CURTAIN
    assert len(_MODEL_TO_MAC_CACHE) == 2

    # Clear cache after test
    _MODEL_TO_MAC_CACHE.clear()


def test_masked_device_id_empty() -> None:
    """Test an empty device identifier is represented safely."""
    assert _masked_device_id("") == "unknown"


def test_extract_region(caplog: pytest.LogCaptureFixture) -> None:
    """Test the _extract_region helper function."""
    caplog.set_level(logging.WARNING, logger="switchbot.devices.device")
    # Test with botRegion present and not empty
    assert _extract_region({"botRegion": "eu", "country": "de"}) == "eu"
    assert _extract_region({"botRegion": "us", "country": "us"}) == "us"
    assert _extract_region({"botRegion": "jp", "country": "jp"}) == "jp"

    # Test with botRegion empty string
    assert _extract_region({"botRegion": "", "country": "de"}) == "us"

    # Test with botRegion missing
    assert _extract_region({"country": "de"}) == "us"

    # Test with empty dict
    assert _extract_region({}) == "us"

    assert "account region missing; defaulting to us" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("commands", "results", "final_result"),
    [
        # All fail -> False
        (("command1", "command2"), [(b"\x01", False), (None, False)], False),
        # First fails -> False (short-circuits, second not called)
        (("command1", "command2"), [(b"\x01", False)], False),
        # First succeeds, second fails -> False
        (("command1", "command2"), [(b"\x01", True), (b"\x01", False)], False),
        # All succeed -> True
        (("command1", "command2"), [(b"\x01", True), (b"\x01", True)], True),
    ],
)
async def test_send_command_sequence(
    commands: tuple[str, ...],
    results: list[tuple[bytes | None, bool]],
    final_result: bool,
) -> None:
    """Test sending command sequence where all must succeed."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotDevice(ble_device)

    device._send_command = AsyncMock(side_effect=[r[0] for r in results])
    device._check_command_result = MagicMock(side_effect=[r[1] for r in results])

    result = await device._send_command_sequence(list(commands))

    assert result is final_result


def test_update_parsed_data_without_advertisement_does_not_log_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Calling _update_parsed_data before any advertisement is a no-op, not an error.

    Regression for #285: previously emitted ``_LOGGER.exception(...)`` outside an
    ``except`` block, which logged "No advertisement data to update / NoneType: None"
    on every press()/turn_on()/update() until the first advertisement arrived.
    """
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotDevice(ble_device)

    assert device._sb_adv_data is None

    with caplog.at_level(logging.DEBUG, logger="switchbot.devices.device"):
        result = device._update_parsed_data({"isOn": True})

    assert result is False
    exception_records = [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]
    assert exception_records == []
    assert all(record.exc_info is None for record in caplog.records)
