from __future__ import annotations

import time
from typing import Any

from bleak import BLEDevice

from switchbot import SwitchbotDevice, SwitchbotModel

SETTINGS_HEADER = "570f68"
COMMAND_SHOW_BATTERY_LEVEL = f"{SETTINGS_HEADER}070108"
COMMAND_TIME_FORMAT = f"{SETTINGS_HEADER}0505"
COMMAND_DATE_FORMAT = f"{SETTINGS_HEADER}070107"

COMMAND_TEMPERATURE_UPDATE_INTERVAL = f"{SETTINGS_HEADER}070105"
COMMAND_CO2_UPDATE_INTERVAL = f"{SETTINGS_HEADER}0b06"
COMMAND_FORCE_NEW_CO2_Measurement = f"{SETTINGS_HEADER}0b04"
COMMAND_CO2_THRESHOLDS = f"{SETTINGS_HEADER}020302"
COMMAND_COMFORTLEVEL = f"{SETTINGS_HEADER}020188"

COMMAND_BUTTON_FUNCTION = f"{SETTINGS_HEADER}070106"
COMMAND_CALIBRATE_CO2_SENSOR = f"{SETTINGS_HEADER}0b02"
COMMAND_SYNC_TIME = "570005030d00000000"

COMMAND_ALERT_SOUND = f"{SETTINGS_HEADER}0204"
COMMAND_ALERT_TEMPERATURE_HUMIDITY = "570f44"
COMMAND_ALERT_CO2 = f"{SETTINGS_HEADER}020301"


class SwitchbotMeter(SwitchbotDevice):
    """
    Only tested with METER_PRO_C. Other devices may or may not work.
    The assumptions that the original app has for each value are noted at the respective method.
    Which of them are actually required by the device is unknown.
    """

    def __init__(
        self,
        device: BLEDevice,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.METER_PRO_C,
        **kwargs: Any,
    ) -> None:
        if model not in (
            SwitchbotModel.METER,
            SwitchbotModel.METER_PRO,
            SwitchbotModel.METER_PRO_C,
        ):
            raise ValueError("initializing SwitchbotMeter with a non-meter model")

        if model != SwitchbotModel.METER_PRO_C:
            print(
                "Initializing SwitchbotMeter with an untested model, Settings may or may not work"
            )

        self._notifications_enabled: bool = False
        self._model = model
        super().__init__(device, None, interface, **kwargs)

    async def show_battery_level(self, show_battery: bool):
        """Show or hide battery level on the display."""
        show_battery_byte = "01" if show_battery else "00"
        await super()._send_command(COMMAND_SHOW_BATTERY_LEVEL + show_battery_byte)

    async def set_time_format(self, format24h: bool):
        """Changes Timeformat on the display. If true 24h mode, else 12h mode."""
        await super()._send_command(COMMAND_TIME_FORMAT + ("00" if format24h else "80"))

    async def set_date_format(self, days_first: bool):
        """Changes Dateformat on the display. If true format is DD/MM, else MM/DD."""
        days_first_byte = "01" if days_first else "00"
        await super()._send_command(COMMAND_DATE_FORMAT + days_first_byte)

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
            raise ValueError("Lower should be smaller than Upper")
        await super()._send_command(
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

        point_five = _get_point_five_byte(cold, hot)
        cold_byte = _encode_temperature(int(cold))
        hot_byte = _encode_temperature(int(hot))

        await super()._send_command(
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

        temperature_point_five = _get_point_five_byte(temperature_low, temperature_high)
        temperature_low_byte = _encode_temperature(int(temperature_low))
        temperature_high_byte = _encode_temperature(int(temperature_high))

        dewpoint_point_five = _get_point_five_byte(dewpoint_low, dewpoint_high)
        dewpoint_low_byte = _encode_temperature(int(dewpoint_low))
        dewpoint_high_byte = _encode_temperature(int(dewpoint_high))

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

        await super()._send_command(
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

    async def set_alert_co2(self, on: bool, co2_low: int, co2_high: max, reverse: bool):
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
        await super()._send_command(
            COMMAND_ALERT_CO2 + f"{mode:02x}" + f"{co2_high:04x}" + f"{co2_low:04x}"
        )

    async def set_temperature_update_interval(self, minutes: int):
        """
        Sets the interval in which temperature and humidity are measured in battery powered mode.
        Original App assumes minutes in {5, 10, 30}
        """
        seconds = minutes * 60
        await super()._send_command(
            COMMAND_TEMPERATURE_UPDATE_INTERVAL + f"{seconds:04x}"
        )

    async def set_co2_update_interval(self, minutes: int):
        """
        Sets the interval in which co2 levels are measured in battery powered mode.
        Original App assumes minutes in {5, 10, 30}
        """
        seconds = minutes * 60
        await super()._send_command(COMMAND_CO2_UPDATE_INTERVAL + f"{seconds:04x}")

    async def set_button_function(self, change_unit: bool, change_data_source: bool):
        """
        Sets the function of te top button:
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
        await super()._send_command(
            COMMAND_BUTTON_FUNCTION + change_unit_byte + change_data_source_byte
        )

    async def force_new_co2_measurement(self):
        """Requests a new CO2 measurement, regardless of update interval"""
        await super()._send_command(COMMAND_FORCE_NEW_CO2_Measurement)

    async def calibrate_co2_sensor(self):
        """
        Calibrate CO2-Sensor.
        Place your device in a well-ventilated area for 1 minute before calling this.
        After calling this the calibration runs for about 5 minutes.
        Keep the device still during this process.
        """
        await super()._send_command(COMMAND_CALIBRATE_CO2_SENSOR)

    async def sync_time(self):
        """Syncs time with System Time"""
        currenttime = hex(int(time.time()))[2:]
        await super()._send_command(COMMAND_SYNC_TIME + currenttime + "00")

    async def set_alert_sound(self, sound_on: bool, volume: int):
        """
        Sets the Alert-Mode.
        If soundOn is False the display flashes.
        If soundOn is True the device additionally beeps.
        The volume is expected to be in {2,3,4} (2: low, 3: medium, 4: high)
        """
        sound_on_byte = "02" if sound_on else "01"
        await super()._send_command(
            COMMAND_ALERT_SOUND + f"{volume:02x}" + sound_on_byte
        )


def _get_point_five_byte(cold: float, hot: float):
    """This byte represents if either of the temperatures has a .5 decimalplace"""
    point_five = 0x00
    if int(cold * 10) % 10 == 5:
        point_five += 0x05
    if int(hot * 10) % 10 == 5:
        point_five += 0x50
    return f"{point_five:02x}"


def _encode_temperature(temp: int):
    # The encoding for a negative temperature is the value as hex
    # The encoding for a positive temperature is the value + 128 as hex
    if temp > 0:
        temp += 128
    else:
        temp *= -1
    return f"{temp:02x}"
