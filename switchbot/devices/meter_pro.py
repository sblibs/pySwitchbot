from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ..const.meter_pro import (
    MeterProAlarmMode,
    MeterProAlarmVolume,
    MeterProCO2AlarmMode,
    MeterProCO2AlarmStatus,
    MeterProComfortStatus,
    MeterProDateFormat,
    MeterProDisplaySource,
    MeterProDisplayZone,
    MeterProWeatherIcon,
    MeterProZoneIcon,
)
from ..helpers import parse_uint24_be
from .device import SwitchbotDevice, SwitchbotOperationError

COMMAND_SET_TIME_OFFSET = "570f680506"
COMMAND_GET_TIME_OFFSET = "570f690506"
MAX_TIME_OFFSET = (1 << 24) - 1

COMMAND_GET_DEVICE_DATETIME = "570f6901"
COMMAND_SET_DEVICE_DATETIME = "57000503"
COMMAND_SET_DISPLAY_FORMAT = "570f680505"

COMMAND_GET_COMFORT_LEVEL = "570f69020101"
COMMAND_SET_COMFORT_LEVEL = "570f680201"
COMMAND_GET_ALARM_SETTINGS = "570f690204"
COMMAND_SET_ALARM_SETTINGS = "570f680204"
COMMAND_GET_CALIBRATION = "570f6903"
COMMAND_SET_CALIBRATION = "570f6803"
COMMAND_GET_DISPLAY_SETTINGS = "570f690701"
COMMAND_SET_DISPLAY_ZONE = "570f680701"
COMMAND_SET_ZONE_ICONS = "570f68070103"
COMMAND_SET_DATA_UPDATE_INTERVAL = "570f68070105"
COMMAND_GET_BUTTON_FUNCTIONS = "570f690704"
COMMAND_SET_BUTTON_FUNCTIONS = "570f68070106"
COMMAND_SET_DATE_FORMAT = "570f68070107"
COMMAND_SET_BATTERY_ICON = "570f68070108"
COMMAND_SET_TEMPERATURE_UNIT = "570f68070109"

MAX_HUMIDITY_CALIBRATION = 99
MAX_DATA_UPDATE_INTERVAL = 0xFFFF
NO_MAC = "000000000000"
# "Keep current value" differs between the single-zone and two-icon commands.
KEEP_ZONE_ICON = 0xFF
KEEP_ICON = 0x0F
KEEP_BUTTON_FUNCTION = 0xFF
KEEP_ALARM_VOLUME = 0xFF
SOURCES_WITHOUT_MAC = {MeterProDisplaySource.NONE, MeterProDisplaySource.NETWORK}
COMMAND_GET_WEATHER = "570f6906"
COMMAND_SET_WEATHER = "570f680601"

COMMAND_TRIGGER_CO2_SAMPLING = "570f680b04"
COMMAND_START_CO2_CALIBRATION = "570f680b02"
COMMAND_GET_USB_POWER_STATE = "570f690b02"
COMMAND_GET_CO2_USB_UPDATE_INTERVAL = "570f690b03"
COMMAND_SET_CO2_USB_UPDATE_INTERVAL = "570f680b01"
COMMAND_GET_CO2_BATTERY_UPDATE_INTERVAL = "570f690b04"
COMMAND_SET_CO2_BATTERY_UPDATE_INTERVAL = "570f680b06"
COMMAND_GET_CO2_ALARM = "570f69020301"
COMMAND_SET_CO2_ALARM = "570f68020301"
COMMAND_GET_CO2_LEVEL_THRESHOLDS = "570f69020302"
COMMAND_SET_CO2_LEVEL_THRESHOLDS = "570f68020302"


def _weather_decimal(value: float | Decimal, name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a number, not a boolean")
    if not isinstance(value, (int, float, Decimal)):
        raise TypeError(f"{name} must be a number")
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    return number


def _encode_weather_temperature(temperature_c: float | Decimal) -> bytes:
    temperature = _weather_decimal(temperature_c, "Temperature")
    if abs(temperature) > Decimal("127.9"):
        raise ValueError("Temperature must be -127.9..127.9 C")
    temperature = temperature.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    integer, decimal = divmod(int(abs(temperature) * 10), 10)
    return bytes((decimal, integer | (0x80 if temperature >= 0 else 0)))


def _decode_comfort_temperature(signed_degrees: int, tenths: int) -> float:
    magnitude = (signed_degrees & 0x7F) * 10 + tenths
    return (magnitude if signed_degrees & 0x80 else -magnitude) / 10


def _encode_weather_humidity(humidity: float | Decimal) -> int:
    relative_humidity = _weather_decimal(humidity, "humidity")
    if not 1 <= relative_humidity <= 99:
        raise ValueError("humidity must be 1..99%")
    return int(relative_humidity.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _encode_weather_icon(icon: MeterProWeatherIcon | int) -> MeterProWeatherIcon:
    if isinstance(icon, MeterProWeatherIcon):
        return icon
    if isinstance(icon, bool) or not isinstance(icon, int):
        raise TypeError("Weather icon must be a MeterProWeatherIcon or integer")
    return MeterProWeatherIcon(icon)


def _mac_hex(mac: str | None) -> str:
    """Return a MAC address as 12 hex digits, all zeros when empty."""
    if not mac:
        return NO_MAC
    cleaned = mac.replace(":", "").replace("-", "").lower()
    if len(cleaned) != 12 or any(c not in "0123456789abcdef" for c in cleaned):
        raise ValueError(f"Invalid MAC address {mac!r}")
    return cleaned


def _format_mac(raw: bytes) -> str | None:
    """Return "AA:BB:CC:DD:EE:FF", or None for an empty MAC."""
    if not any(raw):
        return None
    return ":".join(f"{b:02X}" for b in raw)


class SwitchbotMeterPro(SwitchbotDevice):
    """Implement the shared protocol for SwitchBot Meter Pro and Meter Pro CO2."""

    async def get_time_offset(self) -> int:
        """
        Get the current display time offset from the device.

        Returns:
            int: The time offset in seconds. Max 24 bits.

        """
        # Response Format: 5 bytes, where
        # - byte 0: "01" (success)
        # - byte 1: "00" (plus offset) or "80" (minus offset)
        # - bytes 2-4: int24, number of seconds to offset.
        # Example response: 01-80-00-10-00 -> subtract 4096 seconds.
        result = await self._send_command(COMMAND_GET_TIME_OFFSET)
        result = self._validate_result("get_time_offset", result, min_length=5)

        is_negative = bool(result[1] & 0b10000000)
        offset = parse_uint24_be(result, 2)
        return -offset if is_negative else offset

    async def set_time_offset(self, offset_seconds: int) -> None:
        """
        Set the display time offset on the device. This is what happens when
        you adjust display time in the Switchbot app. The displayed time is
        calculated as the internal device time (usually comes from the factory
        settings or set by the Switchbot app upon syncing) + offset. The offset
        is provided in seconds and can be positive or negative.

        Args:
            offset_seconds (int): 2^24 maximum, can be negative.

        """
        abs_offset = abs(offset_seconds)
        if abs_offset > MAX_TIME_OFFSET:
            raise SwitchbotOperationError(
                f"{self.name}: Requested to set_time_offset of {offset_seconds} seconds, allowed +-{MAX_TIME_OFFSET} max."
            )

        sign_byte = "80" if offset_seconds < 0 else "00"

        # Example: 57-0f-68-05-06-80-00-10-00 -> subtract 4096 seconds.
        payload = f"{COMMAND_SET_TIME_OFFSET}{sign_byte}{abs_offset:06x}"
        result = await self._send_command(payload)
        self._validate_result("set_time_offset", result)

    async def get_datetime(self) -> dict[str, Any]:
        """
        Get the current device time and settings as it is displayed. Contains
        a time offset, if any was applied (see set_time_offset).
        Doesn't include the current time zone.

        Returns:
            dict: Dictionary containing:
                - 12h_mode (bool): True if 12h mode, False if 24h mode.
                - year (int)
                - month (int)
                - day (int)
                - hour (int)
                - minute (int)
                - second (int)

        """
        # Response Format: 13 bytes, where
        # - byte 0: "01" (success)
        # - bytes 1-4: temperature, ignored here.
        # - byte 5: time display format:
        #   - "80" - 12h (am/pm)
        #   - "00" - 24h
        # - bytes 6-12: yyyy-MM-dd-hh-mm-ss
        # Example: 01-e4-02-94-23-00-07-e9-0c-1e-08-37-01 contains
        # "year 2025, 30 December, 08:55:01, displayed in 24h format".
        result = await self._send_command(COMMAND_GET_DEVICE_DATETIME)
        result = self._validate_result("get_datetime", result, min_length=13)
        return {
            # Whether the time is displayed in 12h(am/pm) or 24h mode.
            "12h_mode": bool(result[5] & 0b10000000),
            "year": (result[6] << 8) + result[7],
            "month": result[8],
            "day": result[9],
            "hour": result[10],
            "minute": result[11],
            "second": result[12],
        }

    async def set_datetime(
        self, timestamp: int, utc_offset_hours: int = 0, utc_offset_minutes: int = 0
    ) -> None:
        """
        Set the device internal time and timezone. Similar to how the
        Switchbot app does it upon syncing with the device.
        Pay attention to calculating UTC offset hours and minutes, see
        examples below.

        Args:
            timestamp (int): Unix timestamp in seconds.
            utc_offset_hours (int): UTC offset in hours, floor()'ed,
                within [-12; 14] range.
                Examples: -5 for UTC-05:00, -6 for UTC-05:30,
                5 for UTC+05:00, 5 for UTC+5:30.
            utc_offset_minutes (int): UTC offset minutes component, always
                positive, complements utc_offset_hours.
                Examples: 45 for UTC+05:45, 15 for UTC-5:45.

        """
        if not (-12 <= utc_offset_hours <= 14):
            raise SwitchbotOperationError(
                f"{self.name}: utc_offset_hours must be between -12 and +14 inclusive, got {utc_offset_hours}"
            )
        if not (0 <= utc_offset_minutes < 60):
            raise SwitchbotOperationError(
                f"{self.name}: utc_offset_minutes must be between 0 and 59 inclusive, got {utc_offset_minutes}"
            )

        # The device doesn't automatically add offset minutes, it expects them
        # to come as a part of the timestamp.
        adjusted_timestamp = timestamp + utc_offset_minutes * 60

        # The timezone is encoded as 1 byte, where 00 stands for UTC-12.
        # TZ with minute offset gets floor()ed: 4:30 yields 4, -4:30 yields -5.
        utc_byte = utc_offset_hours + 12

        payload = (
            f"{COMMAND_SET_DEVICE_DATETIME}{utc_byte:02x}"
            f"{adjusted_timestamp:016x}{utc_offset_minutes:02x}"
        )

        result = await self._send_command(payload)
        self._validate_result("set_datetime", result)

    async def set_time_display_format(self, is_12h_mode: bool = False) -> None:
        """
        Set the time display format on the device: 12h(AM/PM) or 24h.

        Args:
            is_12h_mode (bool): True for 12h (AM/PM) mode, False for 24h mode.

        """
        mode_byte = "80" if is_12h_mode else "00"
        payload = f"{COMMAND_SET_DISPLAY_FORMAT}{mode_byte}"
        result = await self._send_command(payload)
        self._validate_result("set_time_display_format", result)

    async def get_comfort_level(
        self,
    ) -> dict[str, float | int | bool | MeterProComfortStatus]:
        """Read the comfort mode, Celsius and %RH limits, and current status."""
        result = await self._send_command(COMMAND_GET_COMFORT_LEVEL)
        data = self._validate_result("get_comfort_level", result, min_length=8)
        mode, high, humid, decimals, low, dry, status = data[1:8]
        high_tenths, low_tenths = decimals >> 4, decimals & 0x0F
        humid &= 0x7F
        dry &= 0x7F
        if (
            mode not in (0, 1)
            or max(high_tenths, low_tenths) > 9
            or max(humid, dry) > 99
        ):
            raise SwitchbotOperationError(
                f"{self.name}: Invalid comfort level response (result={data.hex()})"
            )
        return {
            "custom": mode == 1,
            "temperature_low_c": _decode_comfort_temperature(low, low_tenths),
            "temperature_high_c": _decode_comfort_temperature(high, high_tenths),
            "humidity_low": dry,
            "humidity_high": humid,
            "status": MeterProComfortStatus(status & 0x03),
        }

    async def set_comfort_level(
        self,
        temperature_low_c: float | Decimal,
        temperature_high_c: float | Decimal,
        humidity_low: int,
        humidity_high: int,
        *,
        custom: bool = True,
    ) -> None:
        """Set comfort limits in °C (half-up to tenths) and %RH, or select default mode."""
        try:
            low_tenths, low = _encode_weather_temperature(temperature_low_c)
            high_tenths, high = _encode_weather_temperature(temperature_high_c)
        except (TypeError, ValueError) as exc:
            raise SwitchbotOperationError(f"{self.name}: {exc}") from exc
        if any(
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 0 <= limit <= 99
            for limit in (humidity_low, humidity_high)
        ):
            raise SwitchbotOperationError(
                f"{self.name}: Comfort humidity limits must be integers from 0 to 99"
            )
        if not isinstance(custom, bool):
            raise SwitchbotOperationError(f"{self.name}: custom must be a boolean")
        if custom and (
            _decode_comfort_temperature(low, low_tenths)
            >= _decode_comfort_temperature(high, high_tenths)
            or humidity_low >= humidity_high
        ):
            raise SwitchbotOperationError(
                f"{self.name}: Lower comfort limits must be below upper limits"
            )

        flags = 0x88 if custom else 0x80
        limits = bytes(
            (high, humidity_high, (high_tenths << 4) | low_tenths, low, humidity_low)
        )
        result = await self._send_command(
            f"{COMMAND_SET_COMFORT_LEVEL}{flags:02x}{limits.hex()}"
        )
        self._validate_result("set_comfort_level", result)

    async def get_alarm_settings(
        self,
    ) -> dict[str, MeterProAlarmMode | MeterProAlarmVolume | None]:
        """Read the local alarm mode and volume, with None for an unrecognized volume."""
        result = await self._send_command(COMMAND_GET_ALARM_SETTINGS)
        data = self._validate_result("get_alarm_settings", result, min_length=3)
        try:
            mode = MeterProAlarmMode(data[2])
        except ValueError as exc:
            raise SwitchbotOperationError(
                f"{self.name}: Unknown alarm mode {data[2]:02x}"
            ) from exc
        volume = next(
            (level for level in MeterProAlarmVolume if level.value == data[1]), None
        )
        return {"mode": mode, "volume": volume}

    async def set_alarm_settings(
        self, mode: MeterProAlarmMode, volume: MeterProAlarmVolume | None = None
    ) -> None:
        """Set the local alarm mode and optionally change the buzzer volume."""
        if not isinstance(mode, MeterProAlarmMode):
            raise SwitchbotOperationError(
                f"{self.name}: mode must be a MeterProAlarmMode"
            )
        if volume is not None and not isinstance(volume, MeterProAlarmVolume):
            raise SwitchbotOperationError(
                f"{self.name}: volume must be a MeterProAlarmVolume or None"
            )
        volume_byte = KEEP_ALARM_VOLUME if volume is None else volume.value
        result = await self._send_command(
            f"{COMMAND_SET_ALARM_SETTINGS}{volume_byte:02x}{mode.value:02x}"
        )
        self._validate_result("set_alarm_settings", result)

    async def get_calibration(self) -> dict[str, Any]:
        """Get the temperature (C) and humidity (%RH) corrections."""
        # [status][temp sign|int][hum sign|value][temp tenths]; sign bit = positive
        result = await self._send_command(COMMAND_GET_CALIBRATION)
        result = self._validate_result("get_calibration", result, min_length=4)
        tenths = result[3] & 0x0F
        humidity = result[2] & 0x7F
        if tenths > 9 or humidity > MAX_HUMIDITY_CALIBRATION:
            raise SwitchbotOperationError(
                f"{self.name}: Invalid calibration response "
                f"(result={result.hex()} rssi={self.rssi})"
            )
        temperature = round((result[1] & 0x7F) + tenths / 10, 1)
        # A zero correction comes back with the sign bit cleared.
        return {
            "temperature": temperature if result[1] & 0x80 else -temperature or 0.0,
            "humidity": humidity if result[2] & 0x80 else -humidity,
        }

    async def set_calibration(
        self, temperature: float | Decimal, humidity: int
    ) -> None:
        """Set the temperature (C, rounded half-up to tenths) and humidity corrections."""
        try:
            decimal, temperature_byte = _encode_weather_temperature(temperature)
        except (TypeError, ValueError) as exc:
            raise SwitchbotOperationError(f"{self.name}: {exc}") from exc
        if (
            isinstance(humidity, bool)
            or not isinstance(humidity, int)
            or abs(humidity) > MAX_HUMIDITY_CALIBRATION
        ):
            raise SwitchbotOperationError(
                f"{self.name}: Humidity calibration must be an integer within "
                f"±{MAX_HUMIDITY_CALIBRATION}, got {humidity!r}"
            )
        humidity_byte = abs(humidity) | (0x80 if humidity >= 0 else 0)
        payload = (
            f"{COMMAND_SET_CALIBRATION}{temperature_byte:02x}"
            f"{humidity_byte:02x}{decimal:02x}"
        )
        result = await self._send_command(payload)
        self._validate_result("set_calibration", result)

    async def get_display_settings(self) -> dict[str, Any]:
        """
        Get the zones, data update interval, date format and battery icon.

        Missing fields and unknown date or battery icon values are None.
        Each zone has "icon", "source" (the raw int if unknown) and "source_mac"
        (None when the zone shows this device or network data).
        """
        # [status][icons mid|bot][sources mid|bot][mac mid x6][mac bot x6]
        # [data update interval u16][date format][reserved][battery icon]
        result = await self._send_command(COMMAND_GET_DISPLAY_SETTINGS)
        result = self._validate_result("get_display_settings", result, min_length=15)

        def zone(icon: int, source: int, mac: bytes) -> dict[str, Any]:
            return {
                "icon": next((i for i in MeterProZoneIcon if i.value == icon), None),
                "source": next(
                    (s for s in MeterProDisplaySource if s.value == source), source
                ),
                "source_mac": _format_mac(mac),
            }

        return {
            "middle": zone(result[1] >> 4, result[2] >> 4, result[3:9]),
            "bottom": zone(result[1] & 0x0F, result[2] & 0x0F, result[9:15]),
            "data_update_interval": (
                int.from_bytes(result[15:17], "big") if len(result) >= 17 else None
            ),
            "date_format": (
                MeterProDateFormat(result[17])
                if len(result) >= 18 and result[17] in (0x00, 0x01)
                else None
            ),
            "battery_icon_always": (
                bool(result[19])
                if len(result) >= 20 and result[19] in (0x00, 0x01)
                else None
            ),
        }

    async def set_display_zone(
        self,
        zone: MeterProDisplayZone,
        source: MeterProDisplaySource,
        source_mac: str | None = None,
        icon: MeterProZoneIcon | None = None,
    ) -> None:
        """
        Choose what a screen zone shows; icon None keeps the current icon.

        The device reads the source thermometer over BLE itself. NETWORK shows
        the values written by set_weather. METER_PRO without a MAC is this
        device. The screen applies it at the next data update.
        """
        try:
            mac = _mac_hex(source_mac)
        except ValueError as err:
            raise SwitchbotOperationError(f"{self.name}: {err}") from err
        if mac != NO_MAC and source in SOURCES_WITHOUT_MAC:
            raise SwitchbotOperationError(
                f"{self.name}: {source.name} display source takes no MAC address"
            )
        if mac == NO_MAC and source not in (
            *SOURCES_WITHOUT_MAC,
            MeterProDisplaySource.METER_PRO,
        ):
            raise SwitchbotOperationError(
                f"{self.name}: {source.name} display source needs a MAC address"
            )
        icon_byte = KEEP_ZONE_ICON if icon is None else icon.value
        payload = (
            f"{COMMAND_SET_DISPLAY_ZONE}{zone.value:02x}{icon_byte:02x}"
            f"{source.value:02x}{mac}"
        )
        result = await self._send_command(payload)
        self._validate_result("set_display_zone", result)

    async def set_zone_icons(
        self,
        middle: MeterProZoneIcon | None = None,
        bottom: MeterProZoneIcon | None = None,
    ) -> None:
        """Set the indoor/outdoor icons of both zones; None keeps an icon."""
        middle_byte = KEEP_ICON if middle is None else middle.value
        bottom_byte = KEEP_ICON if bottom is None else bottom.value
        payload = f"{COMMAND_SET_ZONE_ICONS}{middle_byte:02x}{bottom_byte:02x}"
        result = await self._send_command(payload)
        self._validate_result("set_zone_icons", result)

    async def set_data_update_interval(self, seconds: int) -> None:
        """Set the temperature and humidity update interval; the app offers 300, 600 and 1800 s."""
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or not 1 <= seconds <= MAX_DATA_UPDATE_INTERVAL
        ):
            raise SwitchbotOperationError(
                f"{self.name}: Data update interval must be an integer from "
                f"1 to {MAX_DATA_UPDATE_INTERVAL} seconds, got {seconds!r}"
            )
        payload = COMMAND_SET_DATA_UPDATE_INTERVAL + seconds.to_bytes(2, "big").hex()
        result = await self._send_command(payload)
        self._validate_result("set_data_update_interval", result)

    async def set_date_format(self, date_format: MeterProDateFormat) -> None:
        """Set the date format; the app offers it from firmware 1.5."""
        payload = f"{COMMAND_SET_DATE_FORMAT}{date_format.value:02x}"
        result = await self._send_command(payload)
        self._validate_result("set_date_format", result)

    async def set_battery_icon(self, always: bool) -> None:
        """Show the battery icon always, or only when the battery is low."""
        payload = f"{COMMAND_SET_BATTERY_ICON}{'01' if always else '00'}"
        result = await self._send_command(payload)
        self._validate_result("set_battery_icon", result)

    async def set_temperature_unit(self, fahrenheit: bool) -> None:
        """Set the default temperature unit shown on the screen (F or C)."""
        payload = f"{COMMAND_SET_TEMPERATURE_UNIT}{'01' if fahrenheit else '00'}"
        result = await self._send_command(payload)
        self._validate_result("set_temperature_unit", result)

    async def get_button_functions(self) -> dict[str, bool | None]:
        """Read button functions, with None for reserved or unknown values."""
        result = await self._send_command(COMMAND_GET_BUTTON_FUNCTIONS)
        result = self._validate_result("get_button_functions", result, min_length=3)
        # The protocol enables unit switching with 0x00 and source switching with 0x01.
        return {
            "unit_switch": result[1] == 0x00 if result[1] in (0x00, 0x01) else None,
            "source_switch": result[2] == 0x01 if result[2] in (0x00, 0x01) else None,
        }

    async def set_button_functions(
        self, unit_switch: bool | None = None, source_switch: bool | None = None
    ) -> None:
        """Allow or forbid the button actions; None keeps one as is."""
        unit_byte = (
            KEEP_BUTTON_FUNCTION
            if unit_switch is None
            else (0x00 if unit_switch else 0x01)
        )
        source_byte = (
            KEEP_BUTTON_FUNCTION
            if source_switch is None
            else (0x01 if source_switch else 0x00)
        )
        payload = f"{COMMAND_SET_BUTTON_FUNCTIONS}{unit_byte:02x}{source_byte:02x}"
        result = await self._send_command(payload)
        self._validate_result("set_button_functions", result)

    def _validate_result(
        self, op_name: str, result: bytes | None, min_length: int | None = None
    ) -> bytes:
        if not self._check_command_result(result, 0, {1}):
            raise SwitchbotOperationError(
                f"{self.name}: Unexpected response code for {op_name} (result={result.hex() if result else 'None'} rssi={self.rssi})"
            )
        assert result is not None
        if min_length is not None and len(result) < min_length:
            raise SwitchbotOperationError(
                f"{self.name}: Unexpected response len for {op_name}, wanted at least {min_length} (result={result.hex() if result else 'None'} rssi={self.rssi})"
            )
        return result

    def _parse_weather(self, result: bytes | None) -> tuple[MeterProWeatherIcon, bytes]:
        result = self._validate_result("get_weather", result, min_length=5)
        # Only the first five bytes are documented; firmware may append other data.
        try:
            icon = MeterProWeatherIcon(result[1])
        except ValueError as exc:
            raise SwitchbotOperationError(
                f"{self.name}: Unknown weather icon {result[1]} "
                f"(result={result.hex()} rssi={self.rssi})"
            ) from exc
        if result[2] & 0x0F > 9 or result[4] & 0x7F > 99:
            raise SwitchbotOperationError(
                f"{self.name}: Invalid weather measurements "
                f"(result={result.hex()} rssi={self.rssi})"
            )
        return icon, bytes(result[2:5])

    async def get_weather(self) -> dict[str, Any]:
        """Read network weather; unset humidity is None, temperature is independent."""
        icon, network_data = self._parse_weather(
            await self._send_command(COMMAND_GET_WEATHER)
        )
        magnitude = (network_data[1] & 0x7F) + (network_data[0] & 0x0F) / 10
        temperature = magnitude if network_data[1] & 0x80 else -magnitude
        return {
            "icon": icon,
            "temperature_c": temperature if magnitude else 0.0,
            "humidity": (network_data[2] & 0x7F) or None,
            "fahrenheit_display": bool(network_data[2] & 0x80),
        }

    async def _weather_command_locked(self, key: str, retry: int) -> bytes | None:
        command = bytearray.fromhex(self._commandkey(key))
        return await self._send_command_locked_with_retry(
            key, command, retry, retry + 1
        )

    async def set_weather(
        self,
        icon: MeterProWeatherIcon | int | None = None,
        *,
        temperature_c: float | Decimal | None = None,
        humidity: float | Decimal | None = None,
    ) -> None:
        """
        Set supplied weather fields and verify them; preserve omitted fields.

        This does not change display sources or paired external sensor data.
        Updates from other clients can race with the read/write sequence.
        """
        if icon is None and temperature_c is None and humidity is None:
            raise SwitchbotOperationError(
                f"{self.name}: Supply at least one weather field"
            )
        try:
            icon = _encode_weather_icon(icon) if icon is not None else None
            temperature = (
                _encode_weather_temperature(temperature_c)
                if temperature_c is not None
                else None
            )
            relative_humidity = (
                _encode_weather_humidity(humidity) if humidity is not None else None
            )
        except (ValueError, TypeError) as exc:
            raise SwitchbotOperationError(f"{self.name}: {exc}") from exc
        async with self._operation_lock:
            current_icon, network_data = self._parse_weather(
                await self._weather_command_locked(
                    COMMAND_GET_WEATHER, self._retry_count
                )
            )
            icon = current_icon if icon is None else icon
            network = bytearray(network_data)
            if temperature is not None:
                network[0] = (network[0] & 0xF0) | temperature[0]
                network[1] = temperature[1]
            if relative_humidity is not None:
                network[2] = (network[2] & 0x80) | relative_humidity
            # Six-byte writes reset network readings; omit only external blocks.
            payload = f"{COMMAND_SET_WEATHER}{icon.value:02x}{network.hex()}"
            # A lost ACK can follow a successful write; do not replay stale readings.
            self._validate_result(
                "set_weather", await self._weather_command_locked(payload, 0)
            )
            updated_icon, updated_network = self._parse_weather(
                await self._weather_command_locked(
                    COMMAND_GET_WEATHER, self._retry_count
                )
            )
            if updated_icon != icon or updated_network != network:
                raise SwitchbotOperationError(
                    f"{self.name}: Weather readback mismatch; no rollback attempted "
                    f"(expected_icon={icon.value} expected_network={network.hex()} "
                    f"actual_icon={updated_icon.value} actual_network={updated_network.hex()} "
                    f"rssi={self.rssi})"
                )


class SwitchbotMeterProCO2(SwitchbotMeterPro):
    """Control the CO2 variant of the SwitchBot Meter Pro."""

    async def trigger_co2_sampling(self) -> None:
        """Request a CO2 sample and wait for the device to acknowledge the request."""
        result = await self._send_command(COMMAND_TRIGGER_CO2_SAMPLING, retry=0)
        self._validate_result("trigger_co2_sampling", result)

    async def start_co2_calibration(self) -> None:
        """
        Start manual calibration and wait for acknowledgement.

        Place the meter outdoors in a well-ventilated area for one minute first.
        Keep it still during the five-minute calibration.
        """
        result = await self._send_command(COMMAND_START_CO2_CALIBRATION, retry=0)
        self._validate_result("start_co2_calibration", result)

    async def is_usb_powered(self) -> bool:
        """Read whether USB-C power is connected."""
        result = await self._send_command(COMMAND_GET_USB_POWER_STATE)
        data = self._validate_result("is_usb_powered", result, min_length=2)
        if data[1] not in (0, 1):
            raise SwitchbotOperationError(
                f"{self.name}: Unexpected USB power state {data[1]:02x}"
            )
        return data[1] == 1

    async def get_co2_battery_update_interval(self) -> int:
        """Read the battery-powered CO2 update interval in seconds."""
        return await self._get_co2_update_interval(
            COMMAND_GET_CO2_BATTERY_UPDATE_INTERVAL, "get_co2_battery_update_interval"
        )

    async def set_co2_battery_update_interval(self, seconds: int) -> None:
        """Set the battery-powered CO2 update interval in seconds."""
        await self._set_co2_update_interval(
            COMMAND_SET_CO2_BATTERY_UPDATE_INTERVAL,
            "set_co2_battery_update_interval",
            seconds,
        )

    async def get_co2_usb_update_interval(self) -> int:
        """Read the USB-powered CO2 update interval in seconds."""
        return await self._get_co2_update_interval(
            COMMAND_GET_CO2_USB_UPDATE_INTERVAL, "get_co2_usb_update_interval"
        )

    async def set_co2_usb_update_interval(self, seconds: int) -> None:
        """Set the USB-powered CO2 update interval in seconds."""
        await self._set_co2_update_interval(
            COMMAND_SET_CO2_USB_UPDATE_INTERVAL, "set_co2_usb_update_interval", seconds
        )

    async def _get_co2_update_interval(self, command: str, operation: str) -> int:
        result = await self._send_command(command)
        data = self._validate_result(operation, result, min_length=3)
        return int.from_bytes(data[1:3], "big")

    async def _set_co2_update_interval(
        self, command: str, operation: str, seconds: int
    ) -> None:
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or not 1 <= seconds <= 0xFFFF
        ):
            raise SwitchbotOperationError(
                f"{self.name}: CO2 update interval must be an integer from 1 to 65535 seconds"
            )

        result = await self._send_command(command + seconds.to_bytes(2, "big").hex())
        self._validate_result(operation, result)

    async def get_co2_alarm(
        self,
    ) -> dict[str, MeterProCO2AlarmMode | MeterProCO2AlarmStatus | int]:
        """Read CO2 alarm conditions, limits in ppm, and current alarm status."""
        result = await self._send_command(COMMAND_GET_CO2_ALARM)
        data = self._validate_result("get_co2_alarm", result, min_length=7)
        return {
            "mode": MeterProCO2AlarmMode(data[1]),
            "high_ppm": int.from_bytes(data[2:4], "big"),
            "low_ppm": int.from_bytes(data[4:6], "big"),
            "status": MeterProCO2AlarmStatus(data[6] & 0x03),
        }

    async def set_co2_alarm(
        self, mode: MeterProCO2AlarmMode, low_ppm: int, high_ppm: int
    ) -> None:
        """
        Set CO2 alarm conditions and limits in ppm.

        Pass the existing limits when disabling an alarm to keep them configured.
        """
        if not isinstance(mode, MeterProCO2AlarmMode) or mode.value & ~0x0F:
            raise SwitchbotOperationError(
                f"{self.name}: Invalid CO2 alarm mode {mode!r}"
            )
        if any(
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 0 <= limit <= 0xFFFF
            for limit in (low_ppm, high_ppm)
        ):
            raise SwitchbotOperationError(
                f"{self.name}: CO2 alarm limits must be unsigned 16-bit integers"
            )
        if low_ppm > high_ppm:
            raise SwitchbotOperationError(
                f"{self.name}: Lower CO2 alarm limit must not exceed the upper limit"
            )
        payload = (
            bytes((mode.value,))
            + high_ppm.to_bytes(2, "big")
            + low_ppm.to_bytes(2, "big")
        )
        result = await self._send_command(COMMAND_SET_CO2_ALARM + payload.hex())
        self._validate_result("set_co2_alarm", result)

    async def get_co2_level_thresholds(self) -> tuple[int, int]:
        """Read the green-to-yellow and yellow-to-red CO2 thresholds in ppm."""
        result = await self._send_command(COMMAND_GET_CO2_LEVEL_THRESHOLDS)
        data = self._validate_result("get_co2_level_thresholds", result, min_length=5)
        return int.from_bytes(data[1:3], "big"), int.from_bytes(data[3:5], "big")

    async def set_co2_level_thresholds(
        self, green_to_yellow_ppm: int, yellow_to_red_ppm: int
    ) -> None:
        """Set the green-to-yellow and yellow-to-red CO2 thresholds in 100 ppm steps."""
        if any(
            isinstance(threshold, bool)
            or not isinstance(threshold, int)
            or not 0 <= threshold <= 0xFFFF
            or threshold % 100
            for threshold in (green_to_yellow_ppm, yellow_to_red_ppm)
        ):
            raise SwitchbotOperationError(
                f"{self.name}: CO2 level thresholds must be unsigned 16-bit integers in 100 ppm steps"
            )
        if green_to_yellow_ppm >= yellow_to_red_ppm:
            raise SwitchbotOperationError(
                f"{self.name}: The green-to-yellow CO2 threshold must be below the yellow-to-red threshold"
            )

        payload = (
            COMMAND_SET_CO2_LEVEL_THRESHOLDS
            + (
                green_to_yellow_ppm.to_bytes(2, "big")
                + yellow_to_red_ppm.to_bytes(2, "big")
            ).hex()
        )
        result = await self._send_command(payload)
        self._validate_result("set_co2_level_thresholds", result)
