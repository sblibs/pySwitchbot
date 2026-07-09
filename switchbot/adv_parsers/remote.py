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
    """
    Process Universal Remote adv data.

    The battery level and charging state are encoded in the manufacturer
    specific data. ADV byte 14 maps to ``mfr_data[9]`` (the manufacturer data
    starts at ADV byte 5):

    - bit 7: charging state (0 = not charging, 1 = charging)
    - bits 6-0: battery level (1-100%)
    """
    if mfr_data is None or len(mfr_data) < 10:
        return {
            "battery": None,
            "charging": None,
        }

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())

    return {
        "battery": mfr_data[9] & 0b01111111,
        "charging": bool((mfr_data[9] >> 7) & 1),
    }
