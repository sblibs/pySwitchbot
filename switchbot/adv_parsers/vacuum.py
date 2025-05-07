"""Vacuum parser."""

from __future__ import annotations

import struct


def process_vacuum(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Support for s10, k10+ pro combo, k20 process service data."""
    if mfr_data is None:
        return {}

    _seq_num = mfr_data[6]
    _soc_version = get_device_fw_version(mfr_data[8:11])
    # Steps at the end of the last network configuration
    _step = mfr_data[11] & 0b00001111
    _mqtt_connected = bool(mfr_data[11] & 0b00010000)
    _battery = mfr_data[12]
    _work_status = mfr_data[13] & 0b00111111

    return {
        "sequence_number": _seq_num,
        "soc_version": _soc_version,
        "step": _step,
        "mqtt_connected": _mqtt_connected,
        "battery": _battery,
        "work_status": _work_status,
    }


def get_device_fw_version(version_bytes: bytes) -> str | None:
    version1 = version_bytes[0] & 0x0F
    version2 = version_bytes[0] >> 4
    version3 = struct.unpack("<H", version_bytes[1:])[0]
    return f"{version1}.{version2}.{version3:>03d}"


def process_vacuum_k(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str]:
    """Support for k10+, k10+ pro process service data."""
    if mfr_data is None:
        return {}

    _seq_num = mfr_data[6]
    _dustbin_bound = bool(mfr_data[7] & 0b10000000)
    _dusbin_connected = bool(mfr_data[7] & 0b01000000)
    _network_connected = bool(mfr_data[7] & 0b00100000)
    _work_status = (mfr_data[7] & 0b00010000) >> 4
    _battery = mfr_data[8] & 0b01111111

    return {
        "sequence_number": _seq_num,
        "dustbin_bound": _dustbin_bound,
        "dusbin_connected": _dusbin_connected,
        "network_connected": _network_connected,
        "work_status": _work_status,
        "battery": _battery,
    }
