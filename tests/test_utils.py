"""Tests for utils.py functionality."""

from __future__ import annotations

import pytest

from switchbot.utils import extract_request_id, format_mac_upper


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        pytest.param({"X-Request-ID": "request-id"}, "request-id", id="request-id"),
        pytest.param(
            {"X-Amzn-RequestId": "amazon-request-id"},
            "amazon-request-id",
            id="amazon-request-id",
        ),
        pytest.param({"CF-Ray": "cloudflare-id"}, "cloudflare-id", id="cf-ray"),
        pytest.param({"other": "value"}, None, id="no-request-id"),
        pytest.param({}, None, id="no-headers"),
    ],
)
def test_extract_request_id(headers: dict[str, str], expected: str | None) -> None:
    """Test provider request IDs are extracted case-insensitively."""
    assert extract_request_id(headers) == expected


def test_format_mac_upper() -> None:
    """Test the format_mac_upper utility function."""
    # Test already formatted with colons (lowercase)
    assert format_mac_upper("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:DD:EE:FF"

    # Test already formatted with colons (uppercase)
    assert format_mac_upper("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"

    # Test with dashes
    assert format_mac_upper("aa-bb-cc-dd-ee-ff") == "AA:BB:CC:DD:EE:FF"
    assert format_mac_upper("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:DD:EE:FF"

    # Test with dots (Cisco format)
    assert format_mac_upper("aabb.ccdd.eeff") == "AA:BB:CC:DD:EE:FF"
    assert format_mac_upper("AABB.CCDD.EEFF") == "AA:BB:CC:DD:EE:FF"

    # Test without separators
    assert format_mac_upper("aabbccddeeff") == "AA:BB:CC:DD:EE:FF"
    assert format_mac_upper("AABBCCDDEEFF") == "AA:BB:CC:DD:EE:FF"

    # Test mixed case without separators
    assert format_mac_upper("AaBbCcDdEeFf") == "AA:BB:CC:DD:EE:FF"

    # Test invalid formats (should return original in uppercase)
    assert format_mac_upper("invalid") == "INVALID"
    assert format_mac_upper("aa:bb:cc") == "AA:BB:CC"  # Too short
    assert (
        format_mac_upper("aa:bb:cc:dd:ee:ff:gg") == "AA:BB:CC:DD:EE:FF:GG"
    )  # Too long

    # Test edge cases
    assert format_mac_upper("") == ""
    assert format_mac_upper("123456789ABC") == "12:34:56:78:9A:BC"
    assert format_mac_upper("12:34:56:78:9a:bc") == "12:34:56:78:9A:BC"
