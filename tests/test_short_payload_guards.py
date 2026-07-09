"""
Regression tests: parsers must not raise on short payloads.

The dispatcher in `switchbot/adv_parser.py` does not pre-validate
`mfr_data` / `data` length before invoking parsers. A malformed BLE
advertisement (untrusted but range-limited input) should degrade to
an empty dict / None values, not raise an `IndexError` / `ValueError`
that bubbles up to callers.
"""

from __future__ import annotations

import pytest

from switchbot.adv_parsers.air_purifier import process_air_purifier
from switchbot.adv_parsers.art_frame import process_art_frame
from switchbot.adv_parsers.blind_tilt import process_woblindtilt
from switchbot.adv_parsers.bot import process_wohand
from switchbot.adv_parsers.bulb import process_color_bulb
from switchbot.adv_parsers.ceiling_light import process_woceiling
from switchbot.adv_parsers.climate_panel import process_climate_panel
from switchbot.adv_parsers.curtain import process_wocurtain
from switchbot.adv_parsers.fan import process_fan, process_standing_fan
from switchbot.adv_parsers.hub2 import process_wohub2
from switchbot.adv_parsers.hub3 import process_hub3
from switchbot.adv_parsers.hubmini_matter import process_hubmini_matter
from switchbot.adv_parsers.humidifier import (
    process_evaporative_humidifier,
    process_wohumidifier,
)
from switchbot.adv_parsers.keypad import process_wokeypad
from switchbot.adv_parsers.keypad_vision import (
    process_keypad_vision,
    process_keypad_vision_pro,
)
from switchbot.adv_parsers.light_strip import (
    process_candle_warmer_lamp,
    process_light,
    process_rgbic_light,
    process_wostrip,
)
from switchbot.adv_parsers.lock import (
    parse_common_data,
    process_lock2,
    process_locklite,
    process_wolock,
    process_wolock_pro,
)
from switchbot.adv_parsers.meter import process_wosensorth
from switchbot.adv_parsers.motion import process_wopresence
from switchbot.adv_parsers.plug import process_woplugmini
from switchbot.adv_parsers.remote import process_woremote, process_wouniversal_remote
from switchbot.adv_parsers.roller_shade import process_worollershade
from switchbot.adv_parsers.smart_thermostat_radiator import (
    process_smart_thermostat_radiator,
)
from switchbot.adv_parsers.vacuum import process_vacuum, process_vacuum_k

EMPTY = b""
SHORT = b"\x00" * 4


@pytest.mark.parametrize(
    "parser",
    [
        process_air_purifier,
        process_art_frame,
        process_woblindtilt,
        process_color_bulb,
        process_woceiling,
        process_climate_panel,
        process_wocurtain,
        process_fan,
        process_standing_fan,
        process_wohub2,
        process_hub3,
        process_hubmini_matter,
        process_evaporative_humidifier,
        process_keypad_vision,
        process_keypad_vision_pro,
        process_wostrip,
        process_candle_warmer_lamp,
        process_woplugmini,
        process_worollershade,
        process_smart_thermostat_radiator,
        process_vacuum,
        process_vacuum_k,
    ],
)
@pytest.mark.parametrize("payload", [None, EMPTY, SHORT])
def test_mfr_only_parsers_return_empty_on_short(parser, payload):
    """Parsers that read only mfr_data must return {} for short payloads."""
    assert parser(None, payload) == {}


@pytest.mark.parametrize("payload", [None, EMPTY, SHORT, b"\x00" * 17])
def test_process_light_short_payload(payload):
    """process_light needs cw_offset + 2 bytes (default 18)."""
    assert process_light(None, payload) == {}


@pytest.mark.parametrize("payload", [None, EMPTY, SHORT, b"\x00" * 11])
def test_process_rgbic_light_short_payload(payload):
    """process_rgbic_light uses cw_offset=10, so needs >= 12 bytes."""
    assert process_rgbic_light(None, payload) == {}


@pytest.mark.parametrize(
    ("data", "mfr_data"),
    [
        (None, None),
        (EMPTY, None),
        (b"\x00\x00", None),
    ],
)
def test_process_wohand_short_data(data, mfr_data):
    """process_wohand must not crash on short `data`."""
    out = process_wohand(data, mfr_data)
    # Either an empty dict (both None) or all-None values
    assert "isOn" in out or out == {}
    assert out.get("battery") in (None, *out.values())


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00"])
def test_process_woremote_short_data(data):
    out = process_woremote(data, None)
    assert out == {"battery": None}


@pytest.mark.parametrize(
    "mfr_data",
    [None, EMPTY, b"\x00", b"\x00" * 9],
)
def test_process_wouniversal_remote_short_mfr(mfr_data):
    out = process_wouniversal_remote(None, mfr_data)
    assert out == {"battery": None, "charging": None}


@pytest.mark.parametrize(
    ("data", "mfr_data"),
    [
        (None, None),
        (b"\x00", None),
        (None, b"\x00"),
        (b"\x00\x00", b"\x00\x00"),
    ],
)
def test_process_wokeypad_short(data, mfr_data):
    out = process_wokeypad(data, mfr_data)
    assert out == {"battery": None, "attempt_state": None}


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00\x00"])
def test_process_wohumidifier_short_data(data):
    out = process_wohumidifier(data, None)
    assert out == {"isOn": None, "level": None, "switchMode": True}


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00\x00"])
@pytest.mark.parametrize("mfr_data", [None, EMPTY, b"\x00\x00\x00"])
def test_process_wosensorth_short(data, mfr_data):
    """process_wosensorth must not crash; returns {} when no usable payload."""
    out = process_wosensorth(data, mfr_data)
    assert isinstance(out, dict)


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00\x00"])
@pytest.mark.parametrize("mfr_data", [None, EMPTY, b"\x00\x00\x00"])
def test_process_wopresence_short(data, mfr_data):
    """process_wopresence must not crash even when both inputs are short."""
    out = process_wopresence(data, mfr_data)
    assert isinstance(out, dict)


@pytest.mark.parametrize("mfr_data", [None, EMPTY, SHORT])
def test_lock_parsers_short_mfr(mfr_data):
    assert process_locklite(None, mfr_data) == {}
    assert process_wolock(None, mfr_data) == {}
    assert parse_common_data(mfr_data) == {}
    assert process_wolock_pro(None, mfr_data) == {}
    assert process_lock2(None, mfr_data) == {}


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00"])
def test_blind_tilt_short_data(data):
    """blind_tilt with full mfr but short data must not crash on data[2]."""
    mfr = b"\x00" * 10
    out = process_woblindtilt(data, mfr)
    assert out["battery"] is None


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00"])
def test_curtain_short_data_with_long_mfr(data):
    """Curtain >=11 path uses data[2] for battery; must not crash on short data."""
    mfr = b"\x00" * 11
    out = process_wocurtain(data, mfr)
    assert out["battery"] is None


@pytest.mark.parametrize("data", [b"\x00\x00\x00\x00", b"\x00" * 5])
def test_curtain_short_data_only(data):
    """Curtain data-only path needs len >= 6; shorter -> {}."""
    assert process_wocurtain(data, None) == {}


@pytest.mark.parametrize("data", [None, EMPTY, b"\x00\x00"])
def test_roller_shade_short_data(data):
    """roller_shade with short data must not crash on data[2]."""
    mfr = b"\x00" * 10
    out = process_worollershade(data, mfr)
    assert out["battery"] is None
