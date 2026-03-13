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
@pytest.mark.parametrize(
    ("show_battery", "expected_payload"),
    [
        (True, "01"),
        (False, "00"),
    ],
)
async def test_show_battery_level(show_battery: bool, expected_payload: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.show_battery_level(show_battery=show_battery)
    device._send_command.assert_called_with("570f68070108" + expected_payload)


@pytest.mark.asyncio
async def test_set_co2_thresholds():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_co2_thresholds(lower=500, upper=1000)
    device._send_command.assert_called_with("570f6802030201f403e8")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cold", "hot", "dry", "wet", "expected_payload"),
    [
        (10.0, 20.0, 40, 80, "9450008a28"),
        (-20.0, -10.0, 40, 80, "0a50001428"),
        (-20.0, 70, 40, 80, "c650001428"),
        (0.5, 22, 40, 82, "9652050028"),
        (0, 22, 40, 82, "9652000028"),
        (14, 37.5, 30, 70, "a546508e1e"),
    ],
)
async def test_set_comfortlevel(
    cold: float, hot: float, dry: int, wet: int, expected_payload: str
):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_comfortlevel(cold, hot, dry, wet)
    device._send_command.assert_called_with("570f68020188" + expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "temperature_alert",
        "temperature_low",
        "temperature_high",
        "temperature_reverse",
        "humidity_alert",
        "humidity_low",
        "humidity_high",
        "humidity_reverse",
        "absolute_humidity_alert",
        "absolute_humidity_low",
        "absolute_humidity_high",
        "absolute_humidity_reverse",
        "dewpoint_alert",
        "dewpoint_low",
        "dewpoint_high",
        "dewpoint_reverse",
        "vpd_alert",
        "vpd_low",
        "vpd_high",
        "vpd_reverse",
        "expected_payload",
    ),
    [
        (
            True,
            -20,
            80,
            True,
            False,
            1,
            99,
            False,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "04d063001401bc003c0000a00063630000",
        ),
        (
            True,
            -20,
            59.5,
            True,
            False,
            1,
            99,
            False,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "04bb63501401bc003c0000a00063630000",
        ),
        (
            True,
            -11.5,
            59.5,
            True,
            False,
            1,
            99,
            False,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "04bb63550b01bc003c0000a00063630000",
        ),
        (
            True,
            -11.5,
            59.5,
            False,
            False,
            1,
            99,
            False,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "03bb63550b01bc003c0000a00063630000",
        ),
        (
            True,
            -11.5,
            59.5,
            False,
            True,
            20,
            80,
            False,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "33bb50550b14bc003c0000a00063630000",
        ),
        (
            True,
            -11.5,
            59.5,
            False,
            True,
            20,
            80,
            True,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "43bb50550b14bc003c0000a00063630000",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            True,
            20,
            80,
            True,
            False,
            0.00,
            99.99,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "40bb50550b14bc003c0000a00063630000",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            True,
            15.00,
            70.00,
            False,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "00bb50550b14bc003c0000a00146000f00",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            True,
            17.50,
            69.50,
            True,
            False,
            -60.0,
            60.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "00bb50550b14bc003c0000a00245321132",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            False,
            06.00,
            99.99,
            False,
            True,
            -47.0,
            41.0,
            False,
            False,
            0.00,
            10.00,
            False,
            "00bb50550b14a9002f0000a00c63630600",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            False,
            06.00,
            99.99,
            False,
            True,
            -47.0,
            41.0,
            True,
            False,
            0.00,
            10.00,
            False,
            "00bb50550b14a9002f0000a01063630600",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            False,
            06.00,
            99.99,
            False,
            True,
            -15.5,
            42.5,
            True,
            False,
            0.00,
            10.00,
            False,
            "00bb50550b14aa550f0000a01063630600",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            False,
            06.00,
            99.99,
            False,
            False,
            -15.5,
            42.5,
            True,
            True,
            0.00,
            10.00,
            False,
            "00bb50550b14aa550f0000a06063630600",
        ),
        (
            False,
            -11.5,
            59.5,
            False,
            False,
            20,
            80,
            False,
            False,
            06.00,
            99.99,
            False,
            False,
            -15.5,
            42.5,
            True,
            True,
            1.05,
            8.75,
            True,
            "00bb50550b14aa550f4b05818063630600",
        ),
    ],
)
async def test_set_alert_temperature_humidity(
    temperature_alert: bool,
    temperature_low: float,
    temperature_high: float,
    temperature_reverse: bool,
    humidity_alert: bool,
    humidity_low: int,
    humidity_high: int,
    humidity_reverse: bool,
    absolute_humidity_alert: bool,
    absolute_humidity_low: float,
    absolute_humidity_high: float,
    absolute_humidity_reverse: bool,
    dewpoint_alert: bool,
    dewpoint_low: float,
    dewpoint_high: float,
    dewpoint_reverse: bool,
    vpd_alert: bool,
    vpd_low: float,
    vpd_high: float,
    vpd_reverse: bool,
    expected_payload: str,
):
    # Values based on actual measurements from the app

    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_alert_temperature_humidity(
        temperature_alert,
        temperature_low,
        temperature_high,
        temperature_reverse,
        humidity_alert,
        humidity_low,
        humidity_high,
        humidity_reverse,
        absolute_humidity_alert,
        absolute_humidity_low,
        absolute_humidity_high,
        absolute_humidity_reverse,
        dewpoint_alert,
        dewpoint_low,
        dewpoint_high,
        dewpoint_reverse,
        vpd_alert,
        vpd_low,
        vpd_high,
        vpd_reverse,
    )
    device._send_command.assert_called_with("570f44" + expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("on", "co2_low", "co2_high", "reverse", "expected_payload"),
    [
        (False, 1000, 2000, False, "0007d003e8"),
        (True, 1000, 2000, False, "0307d003e8"),
        (True, 700, 2000, False, "0307d002bc"),
        (True, 700, 1500, False, "0305dc02bc"),
        (True, 700, 1500, True, "0405dc02bc"),
    ],
)
async def test_set_alert_co2(
    on: bool, co2_low: int, co2_high: int, reverse: bool, expected_payload: str
):
    # Values based on actual measurements from the app

    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_alert_co2(on, co2_low, co2_high, reverse)
    device._send_command.assert_called_with("570f68020301" + expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("minutes", "expected_payload"),
    [
        (5, "012c"),
        (10, "0258"),
        (30, "0708"),
    ],
)
async def test_set_temperature_update_interval(minutes: int, expected_payload: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_temperature_update_interval(minutes)
    device._send_command.assert_called_with("570f68070105" + expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("minutes", "expected_payload"),
    [
        (5, "012c"),
        (10, "0258"),
        (30, "0708"),
    ],
)
async def test_set_co2_update_interval(minutes: int, expected_payload: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_co2_update_interval(minutes)
    device._send_command.assert_called_with("570f680b06" + expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("change_unit", "change_data_source", "expected_payload"),
    [
        (True, True, "0001"),
        (True, False, "0000"),
        (False, True, "0101"),
        (False, False, "0100"),
    ],
)
async def test_set_button_function(
    change_unit: bool, change_data_source: bool, expected_payload: str
):
    # Values based on actual measurements from the app

    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_button_function(change_unit, change_data_source)
    device._send_command.assert_called_with("570f68070106" + expected_payload)


@pytest.mark.asyncio
async def test_force_new_co2_measurement():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.force_new_co2_measurement()
    device._send_command.assert_called_with("570f680b04")


@pytest.mark.asyncio
async def test_calibrate_co2_sensor():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.calibrate_co2_sensor()
    device._send_command.assert_called_with("570f680b02")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sound_on", "volume", "expected_payload"),
    [
        (False, 4, "0401"),
        (True, 2, "0202"),
        (True, 3, "0302"),
        (True, 4, "0402"),
    ],
)
async def test_set_alert_sound(sound_on: bool, volume: int, expected_payload: str):
    # Values based on actual measurements from the app

    device = create_device()
    device._send_command.return_value = bytes.fromhex("01")

    await device.set_alert_sound(sound_on, volume)
    device._send_command.assert_called_with("570f680204" + expected_payload)
