"""Humidifier adv parser."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

# mfr_data: 943cc68d3d2e
# data: 650000cd802b6300
# data: 650000cd802b6300
# data: 658000c9802b6300

# Low:  658000c5222b6300
# Med:  658000c5432b6300
# High: 658000c5642b6300
def process_wohumidifier(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process WoHumidifier services data."""
    assert mfr_data is not None
    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    _LOGGER.debug("data: %s", data.hex())

    return {
        "isOn": bool(data[2]),
        "level": data[4],
        "switchMode": True,
    }