"""Remote adv parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def process_woremote(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, int | None]:
    """Process WoRemote adv data."""
    if data is None:
        return {
            "battery": None,
        }

    _LOGGER.debug("data: %s", data.hex())

    return {
        "battery": data[2] & 0b01111111,
    }
