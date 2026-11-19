"""Display and calibration settings of the Meter Pro (and Meter Pro CO2)."""

from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import (
    MeterProAlarmMode,
    MeterProAlarmVolume,
    MeterProCO2AlarmMode,
    MeterProCO2AlarmStatus,
    MeterProComfortStatus,
    MeterProDateFormat,
    MeterProDisplaySource,
    MeterProDisplayZone,
    MeterProZoneIcon,
    SwitchbotOperationError,
)
from switchbot.devices.meter_pro import SwitchbotMeterPro, SwitchbotMeterProCO2


def create_device(cls=SwitchbotMeterPro):
    ble_device = BLEDevice(
        address="aa:bb:cc:dd:ee:ff", name="any", details={"rssi": -80}
    )
    device = cls(ble_device)
    device._send_command = AsyncMock(return_value=bytes.fromhex("01"))
    return device


# Captured from a Meter Pro (firmware 1.9): middle zone shows this device with
# the indoor icon, bottom zone shows an Indoor/Outdoor Meter with the outdoor
# icon, data update every 600 s, DD/MM, battery icon always shown.
DISPLAY_SETTINGS = "011253000000000000d4e5f6a1b2c30258010101"


@pytest.mark.asyncio
async def test_get_display_settings():
    device = create_device()
    device._send_command.return_value = bytes.fromhex(DISPLAY_SETTINGS)

    settings = await device.get_display_settings()

    device._send_command.assert_called_with("570f690701")
    assert settings == {
        "middle": {
            "icon": MeterProZoneIcon.INDOOR,
            "source": MeterProDisplaySource.METER_PRO,
            "source_mac": None,
        },
        "bottom": {
            "icon": MeterProZoneIcon.OUTDOOR,
            "source": MeterProDisplaySource.INDOOR_OUTDOOR_METER,
            "source_mac": "D4:E5:F6:A1:B2:C3",
        },
        "data_update_interval": 600,
        "date_format": MeterProDateFormat.DAY_MONTH,
        "battery_icon_always": True,
    }


@pytest.mark.asyncio
async def test_get_display_settings_factory_state():
    """Factory layout: unused bottom zone, MM/DD, battery icon only when low."""
    device = create_device()
    device._send_command.return_value = bytes.fromhex(
        "0110500000000000000000000000000258000100"
    )

    settings = await device.get_display_settings()

    assert settings["bottom"] == {
        "icon": None,
        "source": MeterProDisplaySource.NONE,
        "source_mac": None,
    }
    assert settings["date_format"] is MeterProDateFormat.MONTH_DAY
    assert settings["battery_icon_always"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("date_code", "battery_code", "date_format", "battery_icon_always"),
    [
        (0x02, 0x00, None, False),
        (0x00, 0xFE, MeterProDateFormat.MONTH_DAY, None),
        (0xFF, 0xFF, None, None),
    ],
)
async def test_get_display_settings_unknown_values(
    date_code: int,
    battery_code: int,
    date_format: MeterProDateFormat | None,
    battery_icon_always: bool | None,
):
    device = create_device()
    response = bytearray.fromhex(DISPLAY_SETTINGS)
    response[17] = date_code
    response[19] = battery_code
    device._send_command.return_value = bytes(response)

    settings = await device.get_display_settings()

    assert settings["date_format"] is date_format
    assert settings["battery_icon_always"] is battery_icon_always
    assert settings["data_update_interval"] == 600


@pytest.mark.asyncio
async def test_get_display_settings_short_response():
    """Older firmware may stop after the MAC addresses."""
    device = create_device()
    device._send_command.return_value = bytes.fromhex(DISPLAY_SETTINGS[:30])

    settings = await device.get_display_settings()

    assert settings["bottom"]["source_mac"] == "D4:E5:F6:A1:B2:C3"
    assert settings["data_update_interval"] is None
    assert settings["date_format"] is None
    assert settings["battery_icon_always"] is None


@pytest.mark.asyncio
async def test_get_display_settings_unknown_source_kept_raw():
    device = create_device()
    device._send_command.return_value = bytes.fromhex(
        "011257000000000000aabbccddeeff0258010101"
    )

    settings = await device.get_display_settings()

    assert settings["bottom"]["source"] == 7


@pytest.mark.asyncio
async def test_get_display_settings_weather_station_and_hub3():
    device = create_device()
    device._send_command.return_value = bytes.fromhex(
        "011289aabbccddee01aabbccddee020258010101"
    )

    settings = await device.get_display_settings()

    assert settings["middle"]["source"] is MeterProDisplaySource.WEATHER_STATION
    assert settings["bottom"]["source"] is MeterProDisplaySource.HUB3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    ["02", "011253000000"],  # error status, then response too short
)
async def test_get_display_settings_failure(response: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    with pytest.raises(SwitchbotOperationError):
        await device.get_display_settings()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("zone", "source", "mac", "icon", "expected_payload"),
    [
        (
            MeterProDisplayZone.BOTTOM,
            MeterProDisplaySource.INDOOR_OUTDOOR_METER,
            "D4:E5:F6:A1:B2:C3",
            MeterProZoneIcon.OUTDOOR,
            "570f680701020203d4e5f6a1b2c3",
        ),
        (
            MeterProDisplayZone.BOTTOM,
            MeterProDisplaySource.NETWORK,
            None,
            MeterProZoneIcon.OUTDOOR,
            "570f680701020206000000000000",
        ),
        (
            MeterProDisplayZone.BOTTOM,
            MeterProDisplaySource.NONE,
            None,
            None,
            "570f68070102ff00000000000000",
        ),
        (
            MeterProDisplayZone.MIDDLE,
            MeterProDisplaySource.METER_PRO,
            None,
            MeterProZoneIcon.INDOOR,
            "570f680701010105000000000000",
        ),
        (
            MeterProDisplayZone.MIDDLE,
            MeterProDisplaySource.METER_PLUS,
            "aa-bb-cc-dd-ee-ff",
            None,
            "570f68070101ff02aabbccddeeff",
        ),
    ],
)
async def test_set_display_zone(
    zone: MeterProDisplayZone,
    source: MeterProDisplaySource,
    mac: str | None,
    icon: MeterProZoneIcon | None,
    expected_payload: str,
):
    device = create_device()

    await device.set_display_zone(zone, source, mac, icon)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "mac"),
    [
        (MeterProDisplaySource.METER, None),  # needs a MAC
        (MeterProDisplaySource.NETWORK, "aa:bb:cc:dd:ee:ff"),  # takes none
        (MeterProDisplaySource.NONE, "aa:bb:cc:dd:ee:ff"),  # takes none
        (MeterProDisplaySource.METER, "aa:bb:cc"),  # malformed
        (MeterProDisplaySource.METER, "zz:bb:cc:dd:ee:ff"),  # malformed
    ],
)
async def test_set_display_zone_invalid(source: MeterProDisplaySource, mac: str):
    device = create_device()

    with pytest.raises(SwitchbotOperationError):
        await device.set_display_zone(MeterProDisplayZone.BOTTOM, source, mac)
    device._send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("middle", "bottom", "expected_payload"),
    [
        (MeterProZoneIcon.INDOOR, MeterProZoneIcon.OUTDOOR, "570f680701030102"),
        (None, MeterProZoneIcon.INDOOR, "570f680701030f01"),
        (MeterProZoneIcon.OUTDOOR, None, "570f68070103020f"),
    ],
)
async def test_set_zone_icons(
    middle: MeterProZoneIcon | None,
    bottom: MeterProZoneIcon | None,
    expected_payload: str,
):
    device = create_device()

    await device.set_zone_icons(middle, bottom)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("seconds", "expected_payload"),
    [(300, "570f68070105012c"), (600, "570f680701050258"), (1800, "570f680701050708")],
)
async def test_set_data_update_interval(seconds: int, expected_payload: str):
    device = create_device()

    await device.set_data_update_interval(seconds)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("seconds", [0, -1, 0x10000, True, 300.0, "300"])
async def test_set_data_update_interval_invalid(seconds: object):
    device = create_device()

    with pytest.raises(SwitchbotOperationError):
        await device.set_data_update_interval(seconds)
    device._send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("date_format", "expected_payload"),
    [
        (MeterProDateFormat.MONTH_DAY, "570f6807010700"),
        (MeterProDateFormat.DAY_MONTH, "570f6807010701"),
    ],
)
async def test_set_date_format(date_format: MeterProDateFormat, expected_payload: str):
    device = create_device()

    await device.set_date_format(date_format)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("always", "expected_payload"),
    [(True, "570f6807010801"), (False, "570f6807010800")],
)
async def test_set_battery_icon(always: bool, expected_payload: str):
    device = create_device()

    await device.set_battery_icon(always)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fahrenheit", "expected_payload"),
    [(True, "570f6807010901"), (False, "570f6807010900")],
)
async def test_set_temperature_unit(fahrenheit: bool, expected_payload: str):
    device = create_device()

    await device.set_temperature_unit(fahrenheit)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("010101", {"unit_switch": False, "source_switch": True}),
        ("010000", {"unit_switch": True, "source_switch": False}),
        ("01ff01", {"unit_switch": None, "source_switch": True}),
        ("0100ff", {"unit_switch": True, "source_switch": None}),
        ("01ffff", {"unit_switch": None, "source_switch": None}),
        ("010202", {"unit_switch": None, "source_switch": None}),
    ],
)
async def test_get_button_functions(response: str, expected: dict[str, bool | None]):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    assert await device.get_button_functions() == expected
    device._send_command.assert_called_with("570f690704")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("unit_switch", "source_switch", "expected_payload"),
    [
        (True, False, "570f680701060000"),
        (False, True, "570f680701060101"),
        (None, True, "570f68070106ff01"),
        (False, None, "570f6807010601ff"),
    ],
)
async def test_set_button_functions(
    unit_switch: bool | None, source_switch: bool | None, expected_payload: str
):
    device = create_device()

    await device.set_button_functions(unit_switch, source_switch)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "temperature", "humidity"),
    [
        ("01000000", 0.0, 0),  # factory state: sign bits cleared
        ("01808000", 0.0, 0),
        ("01018305", -1.5, 3),
        ("01820a03", 2.3, -10),
        ("01800005", 0.5, 0),
    ],
)
async def test_get_calibration(response: str, temperature: float, humidity: int):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    calibration = await device.get_calibration()

    device._send_command.assert_called_with("570f6903")
    assert calibration == {"temperature": temperature, "humidity": humidity}
    assert str(calibration["temperature"]) != "-0.0"


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["0180800a", "0180e400", "01806400"])
async def test_get_calibration_rejects_invalid_values(response: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    with pytest.raises(SwitchbotOperationError, match="Invalid calibration response"):
        await device.get_calibration()


@pytest.mark.asyncio
async def test_get_calibration_short_response():
    device = create_device()
    device._send_command.return_value = bytes.fromhex("0101")

    with pytest.raises(SwitchbotOperationError):
        await device.get_calibration()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("temperature", "humidity", "expected_payload"),
    [
        (0, 0, "570f6803808000"),
        (-1.5, 3, "570f6803018305"),
        (2.3, -10, "570f6803820a03"),
        (0.5, 0, "570f6803808005"),  # positive below one degree keeps its sign
        (-0.5, 0, "570f6803008005"),
        (1.25, 0, "570f6803818003"),  # rounded to one decimal
    ],
)
async def test_set_calibration(
    temperature: float, humidity: int, expected_payload: str
):
    device = create_device()

    await device.set_calibration(temperature, humidity)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("temperature", "humidity"),
    [(128, 0), (-128, 0), (0, 100), (0, -100), (0, True), (0, 0.5), (0, "1")],
)
async def test_set_calibration_invalid(temperature: float, humidity: object):
    device = create_device()

    with pytest.raises(SwitchbotOperationError):
        await device.set_calibration(temperature, humidity)
    device._send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("set_calibration", (1.0, 1)),
        ("set_display_zone", (MeterProDisplayZone.BOTTOM, MeterProDisplaySource.NONE)),
        ("set_zone_icons", (MeterProZoneIcon.INDOOR,)),
        ("set_data_update_interval", (600,)),
        ("set_date_format", (MeterProDateFormat.DAY_MONTH,)),
        ("set_battery_icon", (True,)),
        ("set_temperature_unit", (False,)),
        ("set_button_functions", (True, True)),
    ],
)
async def test_setters_raise_on_device_error(method: str, args: tuple):
    device = create_device()
    device._send_command.return_value = bytes.fromhex("05")  # not supported

    with pytest.raises(SwitchbotOperationError):
        await getattr(device, method)(*args)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args", "expected_payload"),
    [
        ("set_calibration", (1.0, 1), "570f6803818100"),
        (
            "set_display_zone",
            (MeterProDisplayZone.BOTTOM, MeterProDisplaySource.NETWORK),
            "570f68070102ff06000000000000",
        ),
        ("set_zone_icons", (MeterProZoneIcon.INDOOR,), "570f68070103010f"),
        ("set_data_update_interval", (600,), "570f680701050258"),
        ("set_date_format", (MeterProDateFormat.DAY_MONTH,), "570f6807010701"),
        ("set_battery_icon", (True,), "570f6807010801"),
        ("set_temperature_unit", (False,), "570f6807010900"),
        ("set_button_functions", (True, True), "570f680701060001"),
    ],
)
async def test_co2_variant_shares_display_settings(
    method: str, args: tuple, expected_payload: str
):
    device = create_device(SwitchbotMeterProCO2)

    await getattr(device, method)(*args)

    device._send_command.assert_called_with(expected_payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_class", "response", "expected"),
    [
        (
            SwitchbotMeterPro,
            "01009c4600921e00",
            {
                "custom": False,
                "temperature_low_c": 18.0,
                "temperature_high_c": 28.0,
                "humidity_low": 30,
                "humidity_high": 70,
                "status": MeterProComfortStatus.COMFORTABLE,
            },
        ),
        (
            SwitchbotMeterProCO2,
            "010180e3730080fe",
            {
                "custom": True,
                "temperature_low_c": -0.3,
                "temperature_high_c": 0.7,
                "humidity_low": 0,
                "humidity_high": 99,
                "status": MeterProComfortStatus.WET,
            },
        ),
    ],
)
async def test_get_comfort_level(
    device_class: type[SwitchbotMeterPro],
    response: str,
    expected: dict[str, float | int | bool | MeterProComfortStatus],
):
    device = create_device(device_class)
    device._send_command.return_value = bytes.fromhex(response)

    assert await device.get_comfort_level() == expected
    device._send_command.assert_awaited_once_with("570f69020101")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limits", "custom", "expected"),
    [
        ((0.5, 22.34, 40, 82), True, "889652358028"),
        ((-0.5, 0.66, 0, 99), True, "888063750000"),
        ((18.0, 28.0, 30, 70), False, "809c4600921e"),
    ],
)
async def test_set_comfort_level(
    limits: tuple[float, float, int, int], custom: bool, expected: str
):
    device = create_device()

    await device.set_comfort_level(*limits, custom=custom)

    device._send_command.assert_awaited_once_with("570f680201" + expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limits", "custom", "message"),
    [
        ((-128, 28.0, 30, 70), True, "Temperature must be"),
        ((True, 28.0, 30, 70), True, "Temperature must be"),
        ((18.01, 18.04, 30, 70), True, "Lower comfort limits"),
        ((18, 28, 30, 100), True, "Comfort humidity limits"),
        ((18, 28, True, 70), True, "Comfort humidity limits"),
        ((18, 28, 70, 70), True, "Lower comfort limits"),
        ((18, 28, 30, 70), 1, "custom must be a boolean"),
    ],
)
async def test_set_comfort_level_rejects_invalid_input(
    limits: tuple[float, float, int, int], custom: bool, message: str
):
    device = create_device()
    with pytest.raises(SwitchbotOperationError, match=message):
        await device.set_comfort_level(*limits, custom=custom)
    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response", ["02", "01", "01029c4600921e00", "01009c460a921e00", "01009c6400921e00"]
)
async def test_get_comfort_level_rejects_invalid_response(response: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)
    with pytest.raises(SwitchbotOperationError):
        await device.get_comfort_level()


@pytest.mark.asyncio
async def test_set_comfort_level_rejects_device_error():
    device = create_device()
    device._send_command.return_value = b"\x02"
    with pytest.raises(SwitchbotOperationError, match="set_comfort_level"):
        await device.set_comfort_level(18, 28, 30, 70)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_class", "response", "mode", "volume"),
    [
        (SwitchbotMeterPro, "010000", MeterProAlarmMode.DISABLED, None),
        (
            SwitchbotMeterProCO2,
            "010402",
            MeterProAlarmMode.SOUND_AND_FLASH,
            MeterProAlarmVolume.HIGH,
        ),
        (SwitchbotMeterPro, "01ff01", MeterProAlarmMode.FLASH_ONLY, None),
    ],
)
async def test_get_alarm_settings(
    device_class: type[SwitchbotMeterPro],
    response: str,
    mode: MeterProAlarmMode,
    volume: MeterProAlarmVolume | None,
):
    device = create_device(device_class)
    device._send_command.return_value = bytes.fromhex(response)

    assert await device.get_alarm_settings() == {"mode": mode, "volume": volume}
    device._send_command.assert_awaited_once_with("570f690204")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "volume", "payload"),
    [
        (MeterProAlarmMode.DISABLED, None, "ff00"),
        (MeterProAlarmMode.FLASH_ONLY, MeterProAlarmVolume.OFF, "0101"),
        (MeterProAlarmMode.SOUND_AND_FLASH, MeterProAlarmVolume.LOW, "0202"),
        (MeterProAlarmMode.SOUND_AND_FLASH, MeterProAlarmVolume.MEDIUM, "0302"),
        (MeterProAlarmMode.SOUND_AND_FLASH, MeterProAlarmVolume.HIGH, "0402"),
    ],
)
async def test_set_alarm_settings(
    mode: MeterProAlarmMode, volume: MeterProAlarmVolume | None, payload: str
):
    device = create_device()

    await device.set_alarm_settings(mode, volume)

    device._send_command.assert_awaited_once_with("570f680204" + payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["02", "0100", "010403"])
async def test_get_alarm_settings_rejects_invalid_response(response: str):
    device = create_device()
    device._send_command.return_value = bytes.fromhex(response)

    with pytest.raises(SwitchbotOperationError):
        await device.get_alarm_settings()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "volume", "message"),
    [(True, None, "mode must be"), (MeterProAlarmMode.DISABLED, 5, "volume must be")],
)
async def test_set_alarm_settings_rejects_invalid_input(
    mode: object, volume: object, message: str
):
    device = create_device()

    with pytest.raises(SwitchbotOperationError, match=message):
        await device.set_alarm_settings(mode, volume)

    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_alarm_settings_rejects_device_error():
    device = create_device()
    device._send_command.return_value = b"\x02"

    with pytest.raises(SwitchbotOperationError, match="set_alarm_settings"):
        await device.set_alarm_settings(MeterProAlarmMode.DISABLED)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "mode", "status"),
    [
        ("01000578019000", MeterProCO2AlarmMode.DISABLED, MeterProCO2AlarmStatus.NONE),
        (
            "010b05780190fe",
            MeterProCO2AlarmMode.CUSTOM
            | MeterProCO2AlarmMode.LOW
            | MeterProCO2AlarmMode.HIGH,
            MeterProCO2AlarmStatus.HIGH,
        ),
        (
            "01840578019003",
            MeterProCO2AlarmMode(0x84),
            MeterProCO2AlarmStatus.IN_RANGE,
        ),
    ],
)
async def test_get_co2_alarm(
    response: str, mode: MeterProCO2AlarmMode, status: MeterProCO2AlarmStatus
):
    device = create_device(SwitchbotMeterProCO2)
    device._send_command.return_value = bytes.fromhex(response)

    assert await device.get_co2_alarm() == {
        "mode": mode,
        "low_ppm": 400,
        "high_ppm": 1400,
        "status": status,
    }
    device._send_command.assert_awaited_once_with("570f69020301")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "low", "high", "payload"),
    [
        (MeterProCO2AlarmMode.DISABLED, 400, 1400, "0005780190"),
        (MeterProCO2AlarmMode.LOW, 401, 1101, "01044d0191"),
        (MeterProCO2AlarmMode.HIGH, 0, 0xFFFF, "02ffff0000"),
        (
            MeterProCO2AlarmMode.LOW | MeterProCO2AlarmMode.HIGH,
            425,
            2000,
            "0307d001a9",
        ),
        (MeterProCO2AlarmMode.IN_RANGE, 1200, 1200, "0404b004b0"),
        (
            MeterProCO2AlarmMode.HIGH | MeterProCO2AlarmMode.CUSTOM,
            425,
            2000,
            "0a07d001a9",
        ),
    ],
)
async def test_set_co2_alarm(
    mode: MeterProCO2AlarmMode, low: int, high: int, payload: str
):
    device = create_device(SwitchbotMeterProCO2)

    await device.set_co2_alarm(mode, low, high)

    device._send_command.assert_awaited_once_with("570f68020301" + payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["02", "010005780190"])
async def test_get_co2_alarm_rejects_invalid_response(response: str):
    device = create_device(SwitchbotMeterProCO2)
    device._send_command.return_value = bytes.fromhex(response)

    with pytest.raises(SwitchbotOperationError, match="get_co2_alarm"):
        await device.get_co2_alarm()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "low", "high", "message"),
    [
        (True, 400, 1400, "Invalid CO2 alarm mode"),
        (MeterProCO2AlarmMode(0x10), 400, 1400, "Invalid CO2 alarm mode"),
        (MeterProCO2AlarmMode.LOW, True, 1400, "unsigned 16-bit integers"),
        (MeterProCO2AlarmMode.LOW, -1, 1400, "unsigned 16-bit integers"),
        (MeterProCO2AlarmMode.LOW, 400, 0x10000, "unsigned 16-bit integers"),
        (MeterProCO2AlarmMode.LOW, 400, 1400.0, "unsigned 16-bit integers"),
        (MeterProCO2AlarmMode.IN_RANGE, 1400, 400, "Lower CO2 alarm limit"),
    ],
)
async def test_set_co2_alarm_rejects_invalid_input(
    mode: object, low: object, high: object, message: str
):
    device = create_device(SwitchbotMeterProCO2)

    with pytest.raises(SwitchbotOperationError, match=message):
        await device.set_co2_alarm(mode, low, high)

    device._send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_co2_alarm_rejects_device_error():
    device = create_device(SwitchbotMeterProCO2)
    device._send_command.return_value = b"\x02"

    with pytest.raises(SwitchbotOperationError, match="set_co2_alarm"):
        await device.set_co2_alarm(MeterProCO2AlarmMode.DISABLED, 400, 1400)


def test_co2_alarm_is_only_available_on_the_co2_model():
    device = create_device()

    assert not hasattr(device, "get_co2_alarm")
    assert not hasattr(device, "set_co2_alarm")
