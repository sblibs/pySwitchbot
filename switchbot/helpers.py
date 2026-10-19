from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Coroutine
from typing import Any, TypeVar

from bleak.exc import BleakError

_LOGGER = logging.getLogger(__name__)

# Background tasks are opportunistic refreshes, so a dropped BLE exchange is
# expected and retried on the next advertisement or poll.
_TRANSIENT_EXCEPTIONS = (TimeoutError, BleakError, EOFError, BrokenPipeError)

_R = TypeVar("_R")

_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()

# Pre-compiled struct unpack methods for better performance
_UNPACK_UINT16_BE = struct.Struct(">H").unpack_from  # Big-endian unsigned 16-bit
_UNPACK_UINT24_BE = struct.Struct(">I").unpack  # For 3-byte values (read as 4 bytes)


def create_background_task(target: Coroutine[Any, Any, _R]) -> asyncio.Task[_R]:
    """Create a background task."""
    task = asyncio.create_task(target)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_background_task_done)
    return task


def _background_task_done(task: asyncio.Task[Any]) -> None:
    """Drop a finished background task and log its failure, if any."""
    _BACKGROUND_TASKS.discard(task)
    if task.cancelled() or (exc := task.exception()) is None:
        return
    name = getattr(task.get_coro(), "__qualname__", task.get_name())
    if isinstance(exc, _TRANSIENT_EXCEPTIONS):
        _LOGGER.debug("Background task %s failed", name, exc_info=exc)
    else:
        _LOGGER.error("Background task %s failed", name, exc_info=exc)


def parse_power_data(
    data: bytes, offset: int, scale: float = 1.0, mask: int | None = None
) -> float:
    """
    Parse 2-byte power-related data from bytes.

    Args:
        data: Raw bytes data
        offset: Starting offset for the 2-byte value
        scale: Scale factor to divide the raw value by (default: 1.0)
        mask: Optional bitmask to apply (default: None)

    Returns:
        Parsed float value

    """
    if offset + 2 > len(data):
        raise ValueError(
            f"Insufficient data: need at least {offset + 2} bytes, got {len(data)}"
        )

    value = _UNPACK_UINT16_BE(data, offset)[0]
    if mask is not None:
        value &= mask
    return value / scale


def parse_uint24_be(data: bytes, offset: int) -> int:
    """
    Parse 3-byte big-endian unsigned integer.

    Args:
        data: Raw bytes data
        offset: Starting offset for the 3-byte value

    Returns:
        Parsed integer value

    """
    if offset + 3 > len(data):
        raise ValueError(
            f"Insufficient data: need at least {offset + 3} bytes, got {len(data)}"
        )

    # Read 3 bytes and pad with 0 at the beginning for 4-byte struct
    return _UNPACK_UINT24_BE(b"\x00" + data[offset : offset + 3])[0]


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert temperature from Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32
