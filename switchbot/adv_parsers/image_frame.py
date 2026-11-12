"""Advertisement parser for Art Frame Luma and AI Memory Frame."""


def process_image_frame(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Parse the frame's two-byte image index and display flags."""
    if mfr_data is None or len(mfr_data) < 11:
        return {}
    flags = mfr_data[10]
    return {
        "sequence_number": mfr_data[6],
        "battery_charging": bool(mfr_data[7] & 0x80),
        "battery": mfr_data[7] & 0x7F,
        "image_index": int.from_bytes(mfr_data[8:10], "little"),
        "display_size": flags >> 4,
        "display_mode": (flags >> 3) & 1,
        "last_network_status": (flags >> 2) & 1,
        "orientation": (flags >> 1) & 1,
    }
