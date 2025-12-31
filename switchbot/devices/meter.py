from .device import SwitchbotDevice, SwitchbotOperationError


class SwitchbotMeterProCO2(SwitchbotDevice):
    """API to control Switchbot Meter Pro CO2."""

    """
    Command code to set the displayed time offse, which happens whenever you
    manually set the device display time in the Switchbot app.

    The displayed time is calculated as the internal device time (usually comes
    from the factory settings or set by the Switchbot app upon syncing)
    + offset. The offset is provided in seconds and can be
    positive or negative.
    """
    COMMAND_SET_TIME_OFFSET = "570f680506"
    COMMAND_GET_TIME_OFFSET = "570f690506"
    MAX_TIME_OFFSET = 1 << 24 - 1

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
        result = await self._send_command(self.COMMAND_GET_TIME_OFFSET)
        result = self._validate_result(
            'get_time_offset', result, min_length=5)

        is_negative = result[1] == 0x80
        offset = (result[2] << 16) + (result[3] << 8) + result[4]
        return -offset if is_negative else offset

    async def set_time_offset(self, offset_seconds: int):
        """
        Set the display time offset on the device.
        This is what happens when you adjust display time in the Switchbot app.

        Args:
            offset_seconds (int): 2^24 maximum, can be negative.
        """
        abs_offset = abs(offset_seconds)
        if abs_offset > self.MAX_TIME_OFFSET:
            raise SwitchbotOperationError(
                f"{self.name}: Requested to set_time_offset of {offset_seconds} seconds, allowed +-{self.MAX_TIME_OFFSET} max."
            )

        sign_byte = "80" if offset_seconds < 0 else "00"

        # Example: 57-0f-68-05-06-80-00-10-00 -> subtract 4096 seconds.
        payload = self.COMMAND_SET_TIME_OFFSET + \
            sign_byte + f"{abs_offset:06x}"
        result = await self._send_command(payload)

        self._validate_result('set_time_offset', result)

    def _validate_result(self, op_name: str, result: bytes | None, min_length: int | None = None) -> bytes:
        if not self._check_command_result(result, 0, {1}):
            raise SwitchbotOperationError(
                f"{self.name}: Unexpected response code for {op_name} (result={result.hex() if result else "None"} rssi={self.rssi})"
            )
        assert result is not None
        if min_length is not None and len(result) < min_length:
            raise SwitchbotOperationError(
                f"{self.name}: Unexpected response len for {op_name}, wanted at least {min_length} (result={result.hex() if result else "None"} rssi={self.rssi})"
            )
        return result
