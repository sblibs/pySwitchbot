from typing import Any

from ..helpers import parse_uint24_be
from .device import SwitchbotDevice, SwitchbotOperationError

SETTINGS_HEADER = "570f68"
COMMAND_SHOW_BATTERY_LEVEL = f"{SETTINGS_HEADER}070108"
COMMAND_DATE_FORMAT = f"{SETTINGS_HEADER}070107"

COMMAND_TEMPERATURE_UPDATE_INTERVAL = f"{SETTINGS_HEADER}070105"
COMMAND_CO2_UPDATE_INTERVAL = f"{SETTINGS_HEADER}0b06"
COMMAND_FORCE_NEW_CO2_MEASUREMENT = f"{SETTINGS_HEADER}0b04"
COMMAND_CO2_THRESHOLDS = f"{SETTINGS_HEADER}020302"
COMMAND_COMFORTLEVEL = f"{SETTINGS_HEADER}020188"

COMMAND_BUTTON_FUNCTION = f"{SETTINGS_HEADER}070106"
COMMAND_CALIBRATE_CO2_SENSOR = f"{SETTINGS_HEADER}0b02"

COMMAND_ALERT_SOUND = f"{SETTINGS_HEADER}0204"
COMMAND_ALERT_TEMPERATURE_HUMIDITY = "570f44"
COMMAND_ALERT_CO2 = f"{SETTINGS_HEADER}020301"

COMMAND_SET_TIME_OFFSET = f"{SETTINGS_HEADER}0506"
COMMAND_GET_TIME_OFFSET = "570f690506"
MAX_TIME_OFFSET = (1 << 24) - 1

COMMAND_GET_DEVICE_DATETIME = "570f6901"
COMMAND_SET_DEVICE_DATETIME = "57000503"
COMMAND_SET_DISPLAY_FORMAT = f"{SETTINGS_HEADER}0505"


class SwitchbotMeterProCO2(SwitchbotDevice):
    """
    API to control Switchbot Meter Pro CO2.

    The assumptions that the original app has for each value are noted at the respective method.
    Which of them are actually required by the device is unknown.
    """

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

    async def show_battery_level(self, show_battery: bool):
        """Show or hide battery level on the display."""
        show_battery_byte = "01" if show_battery else "00"
        await self._send_command(COMMAND_SHOW_BATTERY_LEVEL + show_battery_byte)

    async def set_co2_thresholds(self, lower: int, upper: int):
        """
        Sets the thresholds to define Air Quality for depiction on display as follows:
        co2 < lower => Good (Green)
        lower < co2 < upper => Moderate (Orange)
        upper < co2 => Poor (Red)

        Original App assumes:
        500 <= lower < upper <= 1900
        lower and upper are multiples of 100
        """
        if lower >= upper:
            raise ValueError("Lower should be smaller than upper")
        await self._send_command(
            COMMAND_CO2_THRESHOLDS + f"{lower:04x}" + f"{upper:04x}"
        )

    async def set_comfortlevel(self, cold: float, hot: float, dry: int, wet: int):
        """
        Sets the Thresholds for comfortable temperature (in C) and humidity to display comfort-level.
        The supported values in the original App are as following:
          Temperature is -20C to 80C in 0.5C steps
          Humidity is 1% to 99% in 1% steps
        """
        if cold >= hot:
            raise ValueError("Cold should be smaller than Hot")
        if dry >= wet:
            raise ValueError("Dry should be smaller than Wet")

        point_five = self._get_point_five_byte(cold, hot)
        cold_byte = self._encode_temperature(int(cold))
        hot_byte = self._encode_temperature(int(hot))

        await self._send_command(
            COMMAND_COMFORTLEVEL
            + hot_byte
            + f"{wet:02x}"
            + point_five
            + cold_byte
            + f"{dry:02x}"
        )

    async def set_alert_temperature_humidity(
        self,
        temperature_alert: bool = False,
        temperature_low: float = -20.0,
        temperature_high: float = 80.0,
        temperature_reverse: bool = False,
        humidity_alert: bool = False,
        humidity_low: int = 1,
        humidity_high: int = 99,
        humidity_reverse: bool = False,
        absolute_humidity_alert: bool = False,
        absolute_humidity_low: float = 0.00,
        absolute_humidity_high: float = 99.99,
        absolute_humidity_reverse: bool = False,
        dewpoint_alert: bool = False,
        dewpoint_low: float = -60.0,
        dewpoint_high: float = 60.0,
        dewpoint_reverse: bool = False,
        vpd_alert: bool = False,
        vpd_low: float = 0.00,
        vpd_high: float = 10.00,
        vpd_reverse: bool = False,
    ):
        """
        Sets Temperature- and Humidity- related alerts.
        *_alert: enable or disable respective alert
        *_low and *_high: The respective ranges
        *_reverse: If False: Alert if measured value is outside of provided range.
                   If True: Alert if measured value is inside of provided range.

        The range-boundaries have different assumptions in the original App:
        Temperature: Between -20℃ and 80℃ in 0.5℃ steps
        Humidity: Between 1% and 99% in 1% steps
        Absolute Humidity: Between 0.00g/m^3 and 99.99g/m^3 in 0.5g/m^3 steps (99.99 instead of 100)
        Dew Point: Between -60℃ and 60℃ in 0.5℃ steps
        VPD: Between 0 kPa and 10 kPa in 0.05 kPa steps
        """
        mode_temp_humid = 0x00
        if temperature_alert:
            if temperature_reverse:
                mode_temp_humid += 0x04
            else:
                mode_temp_humid += 0x03
        if humidity_alert:
            if humidity_reverse:
                mode_temp_humid += 0x40
            else:
                mode_temp_humid += 0x30

        mode_abshumid_dewpoint_vpd = 0x00
        if absolute_humidity_alert:
            if absolute_humidity_reverse:
                mode_abshumid_dewpoint_vpd += 0x02
            else:
                mode_abshumid_dewpoint_vpd += 0x01
        if dewpoint_alert:
            if dewpoint_reverse:
                mode_abshumid_dewpoint_vpd += 0x10
            else:
                mode_abshumid_dewpoint_vpd += 0x0C
        if vpd_alert:
            if vpd_reverse:
                mode_abshumid_dewpoint_vpd += 0x80
            else:
                mode_abshumid_dewpoint_vpd += 0x60

        temperature_point_five = self._get_point_five_byte(
            temperature_low, temperature_high
        )
        temperature_low_byte = self._encode_temperature(int(temperature_low))
        temperature_high_byte = self._encode_temperature(int(temperature_high))

        dewpoint_point_five = self._get_point_five_byte(dewpoint_low, dewpoint_high)
        dewpoint_low_byte = self._encode_temperature(int(dewpoint_low))
        dewpoint_high_byte = self._encode_temperature(int(dewpoint_high))

        absolute_humidity_low_bytes = (
            f"{int(absolute_humidity_low):02x}"
            + f"{int(absolute_humidity_low * 100 % 100):02x}"
        )
        absolute_humidity_high_bytes = (
            f"{int(absolute_humidity_high):02x}"
            + f"{int(absolute_humidity_high * 100 % 100):02x}"
        )

        vpd_bytes = (
            f"{int(vpd_high * 100 % 100):02x}"
            + f"{int(vpd_low * 100 % 100):02x}"
            + f"{int(vpd_high):01x}"
        ) + f"{int(vpd_low):01x}"

        await self._send_command(
            COMMAND_ALERT_TEMPERATURE_HUMIDITY
            + f"{mode_temp_humid:02x}"
            + temperature_high_byte
            + f"{humidity_high:02x}"
            + temperature_point_five
            + temperature_low_byte
            + f"{humidity_low:02x}"
            + dewpoint_high_byte
            + dewpoint_point_five
            + dewpoint_low_byte
            + vpd_bytes
            + f"{mode_abshumid_dewpoint_vpd:02x}"
            + absolute_humidity_high_bytes
            + absolute_humidity_low_bytes
        )

    async def set_alert_co2(self, on: bool, co2_low: int, co2_high: int, reverse: bool):
        """
        Sets the CO2-Alert.
        on: Turn CO2-Alert on or off
        lower and upper: The provided range (between 400ppm and 2000ppm in 100ppm steps)
        reverse: If False: Alert if measured value is outside of provided range.
                 If True: Alert if measured value is inside of provided range.
        """
        if co2_high < co2_low:
            raise ValueError(
                "Upper value should bigger than the lower value. Do you want to use reverse instead?"
            )

        mode = 0x00 if not on else (0x04 if reverse else 0x03)
        await self._send_command(
            COMMAND_ALERT_CO2 + f"{mode:02x}" + f"{co2_high:04x}" + f"{co2_low:04x}"
        )

    async def set_temperature_update_interval(self, minutes: int):
        """
        Sets the interval in which temperature and humidity are measured in battery powered mode.
        Original App assumes minutes in {5, 10, 30}
        """
        seconds = minutes * 60
        await self._send_command(COMMAND_TEMPERATURE_UPDATE_INTERVAL + f"{seconds:04x}")

    async def set_co2_update_interval(self, minutes: int):
        """
        Sets the interval in which co2 levels are measured in battery powered mode.
        Original App assumes minutes in {5, 10, 30}
        """
        seconds = minutes * 60
        await self._send_command(COMMAND_CO2_UPDATE_INTERVAL + f"{seconds:04x}")

    async def set_button_function(self, change_unit: bool, change_data_source: bool):
        """
        Sets the function of the top button:
        Default (both options false): Only update data
        changeUnit: switch between ℃ and ℉
        changeDataSource: switch between display of indoor and outdoor temperature
        """
        change_unit_byte = (
            "00" if change_unit else "01"
        )  # yes, it has to be reversed like this!
        change_data_source_byte = (
            "01" if change_data_source else "00"
        )  # yes, it has to be reversed like this!
        await self._send_command(
            COMMAND_BUTTON_FUNCTION + change_unit_byte + change_data_source_byte
        )

    async def force_new_co2_measurement(self):
        """Requests a new CO2 measurement, regardless of update interval"""
        await self._send_command(COMMAND_FORCE_NEW_CO2_MEASUREMENT)

    async def calibrate_co2_sensor(self):
        """
        Calibrate CO2-Sensor.
        Place your device in a well-ventilated area for 1 minute before calling this.
        After calling this the calibration runs for about 5 minutes.
        Keep the device still during this process.
        """
        await self._send_command(COMMAND_CALIBRATE_CO2_SENSOR)

    async def set_alert_sound(self, sound_on: bool, volume: int):
        """
        Sets the Alert-Mode.
        If soundOn is False the display flashes.
        If soundOn is True the device additionally beeps.
        The volume is expected to be in {2,3,4} (2: low, 3: medium, 4: high)
        """
        sound_on_byte = "02" if sound_on else "01"
        await self._send_command(COMMAND_ALERT_SOUND + f"{volume:02x}" + sound_on_byte)

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

    def _get_point_five_byte(self, cold: float, hot: float):
        """Represents if either of the temperatures has a .5 decimalplace """
        point_five = 0x00
        if int(cold * 10) % 10 == 5:
            point_five += 0x05
        if int(hot * 10) % 10 == 5:
            point_five += 0x50
        return f"{point_five:02x}"

    def _encode_temperature(self, temp: int):
        # The encoding for a negative temperature is the value as hex
        # The encoding for a positive temperature is the value + 128 as hex
        if temp > 0:
            temp += 128
        else:
            temp *= -1
        return f"{temp:02x}"
