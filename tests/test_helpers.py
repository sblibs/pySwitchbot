"""Tests for helper functions."""

import asyncio
import gc
import logging

import pytest

from switchbot.helpers import (
    _BACKGROUND_TASKS,
    create_background_task,
    parse_power_data,
)


async def _drain_background_task(task: asyncio.Task) -> list[dict]:
    """Let a background task finish and collect unhandled-exception reports."""
    loop = asyncio.get_running_loop()
    reports: list[dict] = []
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: reports.append(context))
    try:
        await asyncio.wait([task])
        await asyncio.sleep(0)
        del task
        gc.collect()
        await asyncio.sleep(0)
    finally:
        loop.set_exception_handler(previous_handler)
    return reports


async def _update() -> None:
    raise TimeoutError


async def _parse() -> None:
    raise IndexError("index out of range")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("coro_func", "level", "exc_name"),
    [
        pytest.param(_update, logging.DEBUG, "TimeoutError", id="transient"),
        pytest.param(_parse, logging.ERROR, "IndexError", id="unexpected"),
    ],
)
async def test_background_task_failure_is_logged(
    caplog: pytest.LogCaptureFixture,
    coro_func,
    level: int,
    exc_name: str,
) -> None:
    """Test a failed background task is logged instead of left unretrieved."""
    caplog.set_level(logging.DEBUG, logger="switchbot.helpers")
    pending = set(_BACKGROUND_TASKS)

    reports = await _drain_background_task(create_background_task(coro_func()))

    assert reports == []
    assert pending == _BACKGROUND_TASKS
    [record] = caplog.records
    assert record.levelno == level
    assert record.getMessage() == f"Background task {coro_func.__name__} failed"
    assert record.exc_info[0].__name__ == exc_name


@pytest.mark.asyncio
async def test_background_task_cancelled() -> None:
    """Test a cancelled background task is dropped without errors."""
    task = create_background_task(asyncio.sleep(10))
    await asyncio.sleep(0)
    task.cancel()

    reports = await _drain_background_task(task)

    assert reports == []
    assert task not in _BACKGROUND_TASKS


@pytest.mark.asyncio
async def test_background_task_success() -> None:
    """Test a successful background task is dropped from the set."""

    async def _ok() -> int:
        return 1

    pending = set(_BACKGROUND_TASKS)

    reports = await _drain_background_task(create_background_task(_ok()))

    assert reports == []
    assert pending == _BACKGROUND_TASKS


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
