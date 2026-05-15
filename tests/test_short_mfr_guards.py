"""Regression tests: parsers must not raise IndexError on short mfr_data (#494)."""

from __future__ import annotations

import pytest

from switchbot.adv_parsers.contact import process_wocontact
from switchbot.adv_parsers.leak import process_leak
from switchbot.adv_parsers.presence_sensor import process_presence_sensor


@pytest.mark.parametrize(
    "mfr_data",
    [b"", b"\x00", b"\x00\x01", b"\x00" * 8],
)
def test_process_leak_short_mfr_returns_empty(mfr_data: bytes) -> None:
    """Leak parser must not crash when mfr_data is shorter than 9 bytes."""
    data = b"&\x00N"
    assert process_leak(data, mfr_data) == {}


@pytest.mark.parametrize(
    "mfr_data",
    [b"", b"\x00" * 6, b"\x00" * 11],
)
def test_process_presence_sensor_short_mfr_returns_empty(mfr_data: bytes) -> None:
    """Presence sensor parser must not crash when mfr_data is shorter than 12 bytes."""
    assert process_presence_sensor(None, mfr_data) == {}


def test_process_presence_sensor_none_mfr_returns_empty() -> None:
    assert process_presence_sensor(None, None) == {}


@pytest.mark.parametrize(
    "data,mfr_data",
    [
        (None, b""),
        (None, b"\x00" * 12),
        (b"", None),
        (b"\x00" * 8, None),
        (b"\x00", b"\x00" * 12),
        (b"\x00" * 8, b"\x00" * 12),
    ],
)
def test_process_wocontact_short_payloads_return_empty(
    data: bytes | None, mfr_data: bytes | None
) -> None:
    """Contact parser must not crash when neither payload is long enough."""
    assert process_wocontact(data, mfr_data) == {}


def test_process_wocontact_uses_mfr_when_data_short() -> None:
    """Long mfr_data lets the parser succeed even with short service data."""
    # mfr_data byte 7 = 0xF0 -> motion+light+contact_open+contact_timeout all True
    mfr_data = b"\x00\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x02"
    result = process_wocontact(None, mfr_data)
    assert result["motion_detected"] is True
    assert result["contact_open"] is True
    assert result["contact_timeout"] is True
    assert result["is_light"] is True
    assert result["button_count"] == 2
    assert result["battery"] is None
    assert result["tested"] is None


def test_process_wocontact_uses_data_when_mfr_missing() -> None:
    """Long service data lets the parser succeed without mfr_data."""
    data = b"d@d\x05\x00u\x00\xf8\x12"
    result = process_wocontact(data, None)
    assert result["battery"] == 100
    assert result["motion_detected"] is True
    assert result["contact_open"] is True
    assert result["contact_timeout"] is True
    assert result["is_light"] is True
    assert result["button_count"] == 2
