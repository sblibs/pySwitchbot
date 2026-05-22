"""Contact sensor parser."""

from __future__ import annotations


def process_wocontact(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process woContact Sensor services data."""
    if data is None and mfr_data is None:
        return {}

    has_full_mfr = mfr_data is not None and len(mfr_data) >= 13
    has_full_data = data is not None and len(data) >= 9
    if not has_full_mfr and not has_full_data:
        return {}

    battery = data[2] & 0b01111111 if data and len(data) >= 3 else None
    tested = bool(data[1] & 0b10000000) if data and len(data) >= 2 else None

    if has_full_mfr:
        motion_detected = bool(mfr_data[7] & 0b10000000)
        contact_open = bool(mfr_data[7] & 0b00010000)
        contact_timeout = bool(mfr_data[7] & 0b00100000)
        button_count = mfr_data[12] & 0b00001111
        is_light = bool(mfr_data[7] & 0b01000000)
    else:
        motion_detected = bool(data[1] & 0b01000000)
        contact_open = bool(data[3] & 0b00000010)
        contact_timeout = bool(data[3] & 0b00000100)
        button_count = data[8] & 0b00001111
        is_light = bool(data[3] & 0b00000001)

    return {
        "tested": tested,
        "motion_detected": motion_detected,
        "battery": battery,
        "contact_open": contact_open or contact_timeout,  # timeout still means its open
        "contact_timeout": contact_timeout,
        "is_light": is_light,
        "button_count": button_count,
    }
