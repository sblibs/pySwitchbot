"""Tests for helper functions."""

import pytest

from switchbot.helpers import parse_power_data


def test_parse_power_data_basic():
    """Test basic power data parsing."""
    # Test data: bytes with value 0x1234 (4660 decimal) at offset 0
    data = b"\x12\x34\x56\x78"

    # Test without scale (should return raw value)
    assert parse_power_data(data, 0) == 4660

    # Test with scale of 10
    assert parse_power_data(data, 0, 10.0) == 466.0

    # Test with scale of 100
    assert parse_power_data(data, 0, 100.0) == 46.6


def test_parse_power_data_with_offset():
    """Test power data parsing with different offsets."""
    data = b"\x00\x00\x12\x34\x56\x78"

    # Value at offset 2 should be 0x1234
    assert parse_power_data(data, 2, 10.0) == 466.0

    # Value at offset 4 should be 0x5678
    assert parse_power_data(data, 4, 10.0) == 2213.6


def test_parse_power_data_with_mask():
    """Test power data parsing with bitmask."""
    # Test data: 0xFFFF
    data = b"\xff\xff"

    # Without mask
    assert parse_power_data(data, 0, 10.0) == 6553.5

    # With mask 0x7FFF (clear highest bit)
    assert parse_power_data(data, 0, 10.0, 0x7FFF) == 3276.7


def test_parse_power_data_insufficient_data():
    """Test error handling for insufficient data."""
    data = b"\x12"  # Only 1 byte

    # Should raise ValueError when trying to read 2 bytes
    with pytest.raises(ValueError, match="Insufficient data"):
        parse_power_data(data, 0)

    # Should also fail at offset 1 with 2-byte data
    data = b"\x12\x34"
    with pytest.raises(ValueError, match="Insufficient data"):
        parse_power_data(data, 1)  # Would need to read bytes 1-2


def test_parse_power_data_real_world_examples():
    """Test with real-world examples from relay switch."""
    # Simulate relay switch data structure
    raw_data = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xdc\x00\x0f\x00\xe8"

    # Voltage at offset 9-10: 0x00DC = 220 / 10.0 = 22.0V
    assert parse_power_data(raw_data, 9, 10.0) == 22.0

    # Current at offset 11-12: 0x000F = 15 / 1000.0 = 0.015A
    assert parse_power_data(raw_data, 11, 1000.0) == 0.015

    # Power at offset 13-14: 0x00E8 = 232 / 10.0 = 23.2W
    assert parse_power_data(raw_data, 13, 10.0) == 23.2
