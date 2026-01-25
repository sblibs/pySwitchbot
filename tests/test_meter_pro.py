from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchbotOperationError
from switchbot.devices.meter_pro import MAX_TIME_OFFSET, SwitchbotMeterProCO2


def create_device():
    ble_device = BLEDevice(
        address="aa:bb:cc:dd:ee:ff", name="any", details={"rssi": -80}
    )
    device = SwitchbotMeterProCO2(ble_device)
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
    # Invalid 1st byte
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
        (-4096, "80001000"),  # "80" for negative offset, 001000 for 4097
        (0, "80000000"),
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
