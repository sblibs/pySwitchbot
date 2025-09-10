"""Tests for device.py functionality."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from switchbot import fetch_cloud_devices
from switchbot.adv_parser import _MODEL_TO_MAC_CACHE, populate_model_to_mac_cache
from switchbot.const import (
    SwitchbotAccountConnectionError,
    SwitchbotAuthenticationError,
    SwitchbotModel,
)
from switchbot.devices.device import SwitchbotBaseDevice, _extract_region


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
        assert "extra_field" in caplog.text  # Full item should be logged


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


def test_extract_region() -> None:
    """Test the _extract_region helper function."""
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
