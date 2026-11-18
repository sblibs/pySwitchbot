from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchbotOperationError
from switchbot.devices.meter_pro import (
    MAX_TIME_OFFSET,
    SwitchbotMeterPro,
    SwitchbotMeterProCO2,
)


def create_device(cls=SwitchbotMeterProCO2):
    ble_device = BLEDevice(
        address="aa:bb:cc:dd:ee:ff", name="any", details={"rssi": -80}
    )
    device = cls(ble_device)
    device._send_command = AsyncMock()
    return device


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "device_response",
        "expected_offset",
    ),
    [
        ("0100101bc9", 1055689),  # 01 (success) 00 (plus offset) 10 1b c9 (1055689)
        ("0180101bc9", -1055689),  # 01 (success) 80 (minus offset) 10 1b c9 (1055689)
    ],
)
async def test_get_time_offset(device_response: str, expected_offset: int):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(device_response)

    offset = await device.get_time_offset()
    device._send_command.assert_called_with("570f690506")
    assert offset == expected_offset


@pytest.mark.asyncio
async def test_get_time_offset_failure():
    device = create_device()
    # Invalid 1st byte
    device._send_command.return_value = bytes.fromhex("0080101bc9")

    with pytest.raises(SwitchbotOperationError):
        await device.get_time_offset()
    device._send_command.assert_called_with("570f690506")


@pytest.mark.asyncio
async def test_get_time_offset_wrong_response():
    device = create_device()
    # Response too short (only status byte returned)
    device._send_command.return_value = bytes.fromhex("01")

    with pytest.raises(SwitchbotOperationError):
        await device.get_time_offset()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "offset_sec",
        "expected_payload",
    ),
    [
        (1055689, "00101bc9"),  # "00" for positive offset, 101bc9 for 1055689
        (-4096, "80001000"),  # "80" for negative offset, 001000 for 4096
        (0, "00000000"),
        (-0, "00000000"),  # -0 == 0 in Python
    ],
)
async def test_set_time_offset(offset_sec: int, expected_payload: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_time_offset(offset_sec)
    device._send_command.assert_called_with("570f680506" + expected_payload)


@pytest.mark.asyncio
async def test_set_time_offset_too_large():
    device = create_device()
    with pytest.raises(SwitchbotOperationError):
        await device.set_time_offset(MAX_TIME_OFFSET + 1)

    with pytest.raises(SwitchbotOperationError):
        await device.set_time_offset(-(MAX_TIME_OFFSET + 1))


@pytest.mark.asyncio
async def test_set_time_offset_failure():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("00")

    with pytest.raises(SwitchbotOperationError):
        await device.set_time_offset(100)


@pytest.mark.asyncio
async def test_get_datetime_success():
    device = create_device()
    # Mock response:
    # byte 0: 01 (success)
    # bytes 1-4: e4 02 94 23 (temp, ignored)
    # byte 5: 00 (24h mode)
    # bytes 6-7: 07 e9 (year 2025)
    # byte 8: 0c (Dec)
    # byte 9: 1e (30)
    # byte 10: 08 (Hour)
    # byte 11: 37 (Minute = 55)
    # byte 12: 01 (Second)
    response_hex = "01e40294230007e90c1e083701"
    device._send_command.return_value = bytes.fromhex(response_hex)

    result = await device.get_datetime()
    device._send_command.assert_called_with("570f6901")

    assert result["12h_mode"] is False
    assert result["year"] == 2025
    assert result["month"] == 12
    assert result["day"] == 30
    assert result["hour"] == 8
    assert result["minute"] == 55
    assert result["second"] == 1


@pytest.mark.asyncio
async def test_get_datetime_12h_mode():
    device = create_device()
    # byte 5: 80 (12h mode)
    # Time: 12:00:00
    response_hex = "010000000080000001010c0000"
    device._send_command.return_value = bytes.fromhex(response_hex)

    result = await device.get_datetime()
    device._send_command.assert_called_with("570f6901")

    assert result["12h_mode"] is True
    assert result["year"] == 0
    assert result["month"] == 1
    assert result["day"] == 1
    assert result["hour"] == 12
    assert result["minute"] == 0
    assert result["second"] == 0


@pytest.mark.asyncio
async def test_get_datetime_failure():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("00")

    with pytest.raises(SwitchbotOperationError):
        await device.get_datetime()


@pytest.mark.asyncio
async def test_get_datetime_wrong_response():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("0100")

    with pytest.raises(SwitchbotOperationError):
        await device.get_datetime()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "timestamp",
        "utc_offset_hours",
        "utc_offset_minutes",
        "expected_ts",
        "expected_utc",
        "expected_min",
    ),
    [
        (1709251200, 0, 0, "65e11a80", "0c", "00"),  # 2024-03-01T00:00:00+00:00
        (1709251200, 1, 0, "65e11a80", "0d", "00"),  # 2024-03-01T00:00:00+01:00
        (1709251200, 5, 45, "65e1250c", "11", "2d"),  # 2024-03-01T00:00:00+05:45
        (1709251200, -6, 15, "65e11e04", "06", "0f"),  # 2024-03-01T00:00:00-05:45
    ],
)
async def test_set_datetime(  # noqa: PLR0913
    *,
    timestamp: int,
    utc_offset_hours: int,
    utc_offset_minutes: int,
    expected_ts: str,
    expected_utc: str,
    expected_min: str,
):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_datetime(
        timestamp,
        utc_offset_hours=utc_offset_hours,
        utc_offset_minutes=utc_offset_minutes,
    )

    expected_ts = expected_ts.zfill(16)
    expected_payload = "57000503" + expected_utc + expected_ts + expected_min
    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_hour",
    [-13, 15],
)
async def test_set_datetime_invalid_utc_offset_hours(bad_hour: int):
    device = create_device()
    with pytest.raises(SwitchbotOperationError):
        await device.set_datetime(1709251200, utc_offset_hours=bad_hour)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_min",
    [-1, 60],
)
async def test_set_datetime_invalid_utc_offset_minutes(bad_min: int):
    device = create_device()
    with pytest.raises(SwitchbotOperationError):
        await device.set_datetime(1709251200, utc_offset_minutes=bad_min)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("is_12h_mode", "expected_payload"),
    [
        (True, "80"),
        (False, "00"),
    ],
)
async def test_set_time_display_format(is_12h_mode: bool, expected_payload: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_time_display_format(is_12h_mode=is_12h_mode)
    device._send_command.assert_called_with("570f680505" + expected_payload)


@pytest.mark.asyncio
async def test_set_time_display_format_failure():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("00")

    with pytest.raises(SwitchbotOperationError):
        await device.set_time_display_format(is_12h_mode=True)


@pytest.mark.asyncio
async def test_meter_pro_shares_datetime_protocol_with_co2_variant():
    """The plain Meter Pro (no CO2 sensor) uses the same BLE commands as the CO2 variant."""
    device = create_device(SwitchbotMeterPro)
    device._send_command.return_value = bytes.fromhex("01e40294230007e90c1e083701")

    result = await device.get_datetime()
    device._send_command.assert_called_with("570f6901")
    assert result["year"] == 2025

    device._send_command.return_value = bytes.fromhex("01")
    await device.set_datetime(1709251200)
    device._send_command.assert_called_with(
        "57000503" + "0c" + "65e11a80".zfill(16) + "00"
    )


@pytest.mark.asyncio
async def test_trigger_co2_sampling():
    device = create_device()
    device._send_command.return_value = b"\x01"

    await device.trigger_co2_sampling()

    device._send_command.assert_awaited_once_with("570f680b04", retry=0)


@pytest.mark.asyncio
async def test_start_co2_calibration():
    device = create_device()
    device._send_command.return_value = b"\x01"

    await device.start_co2_calibration()

    device._send_command.assert_awaited_once_with("570f680b02", retry=0)


@pytest.mark.asyncio
@pytest.mark.parametrize(("response", "powered"), [("0100", False), ("0101", True)])
async def test_is_usb_powered(response: str, powered: bool):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    assert await device.is_usb_powered() is powered
    device._send_command.assert_awaited_once_with("570f690b02")


@pytest.mark.asyncio
async def test_is_usb_powered_rejects_unknown_state():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("0102")

    with pytest.raises(SwitchbotOperationError, match="Unexpected USB power state 02"):
        await device.is_usb_powered()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "command", "response", "expected_seconds"),
    [
        ("battery", "570f690b04", "010258", 600),
        ("battery", "570f690b04", "010708", 1800),
        ("usb", "570f690b03", "01003c", 60),
        ("usb", "570f690b03", "010078", 120),
    ],
)
async def test_get_co2_update_interval(
    mode: str, command: str, response: str, expected_seconds: int
):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    assert (
        await getattr(device, f"get_co2_{mode}_update_interval")() == expected_seconds
    )
    device._send_command.assert_awaited_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "command"),
    [("battery", "570f680b06"), ("usb", "570f680b01")],
)
@pytest.mark.parametrize(
    ("seconds", "expected_payload"),
    [
        (1, "0001"),
        (60, "003c"),
        (120, "0078"),
        (600, "0258"),
        (1800, "0708"),
        (65535, "ffff"),
    ],
)
async def test_set_co2_update_interval(
    mode: str, command: str, seconds: int, expected_payload: str
):
    device = create_device()
    device._send_command.return_value = b"\x01"

    await getattr(device, f"set_co2_{mode}_update_interval")(seconds)

    device._send_command.assert_awaited_once_with(command + expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["battery", "usb"])
@pytest.mark.parametrize("seconds", [True, "600", 600.0, -1, 0, 65536, 0x100000])
async def test_set_co2_update_interval_rejects_invalid_input(
    mode: str, seconds: object
):
    device = create_device()

    with pytest.raises(SwitchbotOperationError, match="1 to 65535 seconds"):
        await getattr(device, f"set_co2_{mode}_update_interval")(seconds)

    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_co2_thresholds():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_co2_thresholds(lower=500, upper=1000)
    device._send_command.assert_called_with("570f6802030201f403e8")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("lower", "upper", "expected_error"),
    [
        (600, 500, "Lower threshold should be smaller than upper threshold"),
        (300, 500, "Original App assumes that lower threshold is at least 500"),
        (600, 5000, "Original App assumes that upper threshold is at most 1900"),
    ],
)
async def test_set_co2_thresholds_throws_on_invalid_input(
    lower: int, upper: int, expected_error: str
):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    # Error if lower >= upper
    with pytest.raises(
        SwitchbotOperationError,
        match=expected_error,
    ):
        await device.set_co2_thresholds(lower=lower, upper=upper)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("trigger_co2_sampling", ()),
        ("start_co2_calibration", ()),
        ("is_usb_powered", ()),
        ("get_co2_battery_update_interval", ()),
        ("get_co2_usb_update_interval", ()),
        ("set_co2_usb_update_interval", (120,)),
        ("set_co2_battery_update_interval", (600,)),
    ],
)
@pytest.mark.parametrize(
    ("response", "response_hex"),
    [(None, "None"), (b"\x02", "02"), (b"\x03", "03"), (b"\x05", "05")],
)
async def test_co2_rejects_unsuccessful_responses(
    method: str, args: tuple[int, ...], response: bytes | None, response_hex: str
):
    device = create_device()
    device._send_command.return_value = response

    with pytest.raises(SwitchbotOperationError, match=f"result={response_hex}"):
        await getattr(device, method)(*args)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "response"),
    [
        ("is_usb_powered", "01"),
        ("get_co2_battery_update_interval", "0102"),
        ("get_co2_usb_update_interval", "0100"),
    ],
)
async def test_co2_getters_reject_short_responses(method: str, response: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    with pytest.raises(
        SwitchbotOperationError, match=f"Unexpected response len for {method}"
    ):
        await getattr(device, method)()
