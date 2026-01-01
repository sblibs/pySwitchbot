from datetime import datetime

from .device import SwitchbotDevice, SwitchbotOperationError

COMMAND_SET_TIME_OFFSET = "570f680506"
COMMAND_GET_TIME_OFFSET = "570f690506"
MAX_TIME_OFFSET = 1 << 24 - 1

COMMAND_GET_DEVICE_DATETIME = "570f6901"
COMMAND_SET_DEVICE_DATETIME = "57000503"
COMMAND_SET_DISPLAY_FORMAT = "570f680505"


class SwitchbotMeterProCO2(SwitchbotDevice):
    """API to control Switchbot Meter Pro CO2."""

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

        is_negative = result[1] == 0x80
        offset = (result[2] << 16) + (result[3] << 8) + result[4]
        return -offset if is_negative else offset

    async def set_time_offset(self, offset_seconds: int):
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
        payload = (
            COMMAND_SET_TIME_OFFSET
            + sign_byte
            + f"{abs_offset:06x}"
        )
        result = await self._send_command(payload)
        self._validate_result("set_time_offset", result)

    async def get_datetime(self) -> dict:
        """
        Get the current device time and settings as it is displayed. Contains
        a time offset, if any was applied (see COMMAND_TIME_OFFSET).
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

    async def set_datetime(self, dt: datetime):
        """
        Set the device internal time and timezone. Similar to how the
        Switchbot app does it upon syncing with the device.

        Args:
            dt (datetime): datetime object with timezone information.

        """
        utc_offset = dt.utcoffset()
        if utc_offset is None:
            # Fallback to the local timezone.
            utc_offset = datetime.now().astimezone().utcoffset()
        utc_offset_hours, utc_offset_minutes = 0, 0
        if utc_offset is not None:
            total_minutes = int(utc_offset.total_seconds() // 60)
            # UTC-04:30 tz is represented as -5hrs +30min
            utc_offset_hours, utc_offset_minutes = divmod(total_minutes, 60)

        # The device doesn't automatically add offset minutes, it expects them
        # to come as a part of the timestamp.
        timestamp = int(dt.timestamp()) + utc_offset_minutes * 60

        # The timezone is encoded as 1 byte, where 00 stands for UTC-12.
        # TZ with minute offset gets floor()ed: 4:30 yields 4, -4:30 yields -5.
        utc_byte = utc_offset_hours + 12

        payload = (
            COMMAND_SET_DEVICE_DATETIME
            + f"{utc_byte:02x}"
            + f"{timestamp:016x}"
            + f"{utc_offset_minutes:02x}"
        )

        result = await self._send_command(payload)
        self._validate_result("set_datetime", result)

    async def set_time_display_format(self, is_12h_mode: bool = False):
        """
        Set the time display format on the device: 12h(AM/PM) or 24h.

        Args:
            is_12h_mode (bool): True for 12h (AM/PM) mode, False for 24h mode.

        """
        mode_byte = "80" if is_12h_mode else "00"

        payload = COMMAND_SET_DISPLAY_FORMAT + mode_byte
        result = await self._send_command(payload)
        self._validate_result("set_time_display_format", result)

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
