"""Modern Ceiling Fan advertisement parser."""

from .fan import process_circulator_fan_pro


def process_modern_ceiling_fan(data: bytes | None, mfr_data: bytes | None) -> dict:
    """Parse fan state and its independent CCT and RGB light channels."""
    if mfr_data is None or len(mfr_data) < 17:
        return {}
    result = process_circulator_fan_pro(data, mfr_data)
    mode = (mfr_data[8] >> 4) & 7
    if mode == 6:
        result["mode"] = "reverse"
    result.update(
        {
            "main_light_is_on": bool(mfr_data[10] & 0x80),
            "main_light_brightness": mfr_data[10] & 0x7F,
            "main_light_color_temp": int.from_bytes(mfr_data[11:13], "big"),
            "color_light_is_on": bool(mfr_data[13] & 0x80),
            "color_light_brightness": mfr_data[13] & 0x7F,
            "color_light_mode": mfr_data[14] & 0x0F,
        }
    )
    return result
