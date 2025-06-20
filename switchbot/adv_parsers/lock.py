"""Lock parser."""

from __future__ import annotations

import logging

from ..const.lock import LockStatus

_LOGGER = logging.getLogger(__name__)


def process_wolock(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Support for lock and lock lite process data."""
    common_data = process_locklite(data, mfr_data)
    if not common_data:
        return {}

    common_data["door_open"] = bool(mfr_data[7] & 0b00000100)
    common_data["unclosed_alarm"] = bool(mfr_data[8] & 0b00100000)
    common_data["auto_lock_paused"] = bool(mfr_data[8] & 0b00000010)

    return common_data


def process_locklite(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Support for lock lite process data."""
    if mfr_data is None:
        return {}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    return {
        "sequence_number": mfr_data[6],
        "battery": data[2] & 0b01111111 if data else None,
        "calibration": bool(mfr_data[7] & 0b10000000),
        "status": LockStatus((mfr_data[7] & 0b01110000) >> 4),
        "update_from_secondary_lock": bool(mfr_data[7] & 0b00001000),
        "double_lock_mode": bool(mfr_data[8] & 0b10000000),
        "unlocked_alarm": bool(mfr_data[8] & 0b00010000),
        "night_latch": bool(mfr_data[9] & 0b00000001) if len(mfr_data) > 9 else False,
    }


def parse_common_data(mfr_data: bytes | None) -> dict[str, bool | int]:
    if mfr_data is None:
        return {}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    return {
        "sequence_number": mfr_data[6],
        "calibration": bool(mfr_data[7] & 0b10000000),
        "status": LockStatus((mfr_data[7] & 0b01111000) >> 3),
        "update_from_secondary_lock": bool(mfr_data[8] & 0b11000000),
        "door_open_from_secondary_lock": bool(mfr_data[8] & 0b00100000),
        "door_open": bool(mfr_data[8] & 0b00010000),
        "auto_lock_paused": bool(mfr_data[8] & 0b00001000),
        "battery": mfr_data[9] & 0b01111111,
        "double_lock_mode": bool(mfr_data[10] & 0b10000000),
        "is_secondary_lock": bool(mfr_data[10] & 0b01000000),
        "manual_unlock_linkage": bool(mfr_data[10] & 0b00100000),
        "unclosed_alarm": bool(mfr_data[11] & 0b10000000),
        "unlocked_alarm": bool(mfr_data[11] & 0b01000000),
        "night_latch": False,
    }


def process_wolock_pro(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Support for lock pro process data."""
    common_data = parse_common_data(mfr_data)
    if not common_data:
        return {}

    lock_pro_data = {
        "low_temperature_alarm": bool(mfr_data[11] & 0b00100000),
        "left_battery_compartment_alarm": mfr_data[11] & 0b000000100,
        "right_battery_compartment_alarm": mfr_data[11] & 0b000000010,
    }
    return common_data | lock_pro_data


def process_lock2(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Support for lock2 process data."""
    common_data = parse_common_data(mfr_data)
    if not common_data:
        return {}

    lock2_data = {
        "power_alarm": bool(mfr_data[11] & 0b00010000),
        "battery_status": mfr_data[11] & 0b00000111,
    }

    return common_data | lock2_data
