"""Display and calibration settings of the Meter Pro (and Meter Pro CO2)."""

from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import (
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
    """Factory layout: bottom zone unused, MM/DD; unknown values stay raw."""
    device = create_device()
    device._send_command.return_value = bytes.fromhex(
        "011050000000000000000000000000025800010" + "0"
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
@pytest.mark.parametrize("seconds", [0, -1, 0x10000])
async def test_set_data_update_interval_invalid(seconds: int):
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
    ],
)
async def test_get_button_functions(response: str, expected: dict[str, bool]):
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
    [(128, 0), (-128, 0), (0, 100), (0, -100)],
)
async def test_set_calibration_out_of_range(temperature: float, humidity: int):
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
