"""Hub4 advertisement parser."""

from __future__ import annotations

from typing import Any

from .hub3 import process_hub3


def process_hub4(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Parse Hub4 sensor data and its 20-level light reading."""
    parsed = process_hub3(data, mfr_data)
    if not parsed:
        return {}
    parsed["lightLevel"] = mfr_data[12] & 0x1F
    # Hub4 has no documented lux mapping for its 20 light levels.
    parsed.pop("illuminance")
    return parsed
