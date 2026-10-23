"""Remote adv parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def process_woremote(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, int | None]:
    """Process WoRemote adv data."""
    if data is None or len(data) < 3:
        return {
            "battery": None,
        }

    _LOGGER.debug("data: %s", data.hex())

    return {
        "battery": data[2] & 0b01111111,
    }


def process_wouniversal_remote(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | None]:
    """Process Universal Remote adv data."""
    if mfr_data is None or len(mfr_data) < 8:
        return {
            "battery": None,
            "charging": None,
        }

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())

    # mfr_data[7]: bit 7 is charging; bits 6-0 are battery percentage.
    return {
        "battery": mfr_data[7] & 0b01111111,
        "charging": bool((mfr_data[7] >> 7) & 1),
    }
