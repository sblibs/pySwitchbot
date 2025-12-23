"""Art Frame advertisement data parser."""

import logging

_LOGGER = logging.getLogger(__name__)


def process_art_frame(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Process Art Frame data."""
    if mfr_data is None:
        return {}

    _seq_num = mfr_data[6]
    battery_charging = bool(mfr_data[7] & 0x80)
    battery = mfr_data[7] & 0x7F
    image_index = mfr_data[8]
    display_size = (mfr_data[9] >> 4) & 0x0F
    display_mode = (mfr_data[9] >> 3) & 0x01
    last_network_status = (mfr_data[9] >> 2) & 0x01

    result = {
        "sequence_number": _seq_num,
        "battery_charging": battery_charging,
        "battery": battery,
        "image_index": image_index,
        "display_size": display_size,
        "display_mode": display_mode,
        "last_network_status": last_network_status,
    }

    _LOGGER.debug("Art Frame mfr data: %s, result: %s", mfr_data.hex(), result)

    return result
