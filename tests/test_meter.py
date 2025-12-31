from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from datetime import datetime
from switchbot import SwitchbotOperationError
from switchbot.devices.meter import SwitchbotMeterProCO2


class TestSwitchbotMeterProCO2:
    def create_device(self):
        ble_device = BLEDevice(address="aa:bb:cc:dd:ee:ff",
                               name="any", details={"rssi": -80})
        device = SwitchbotMeterProCO2(ble_device)
        device._send_command = AsyncMock()
        return device

    @pytest.mark.asyncio
    async def test_get_time_offset_positive(self):
        device = self.create_device()
        # Mock response: 01 (success) 00 (plus offset) 10 1b c9 (1055689 seconds)
        device._send_command.return_value = bytes.fromhex("0100101bc9")

        offset = await device.get_time_offset()
        device._send_command.assert_called_with("570f690506")
        assert offset == 1055689

    @pytest.mark.asyncio
    async def test_get_time_offset_negative(self):
        device = self.create_device()
        # Mock response: 01 (success) 80 (minus offset) 10 1b c9 (1055689 seconds)
        device._send_command.return_value = bytes.fromhex("0180101bc9")

        offset = await device.get_time_offset()
        device._send_command.assert_called_with("570f690506")
        assert offset == -1055689

    @pytest.mark.asyncio
    async def test_get_time_offset_failure(self):
        device = self.create_device()
        # Invalid 1st byte
        device._send_command.return_value = bytes.fromhex("0080101bc9")

        with pytest.raises(SwitchbotOperationError):
            await device.get_time_offset()
        device._send_command.assert_called_with("570f690506")

    @pytest.mark.asyncio
    async def test_get_time_offset_wrong_response(self):
        device = self.create_device()
        # Invalid 1st byte
        device._send_command.return_value = bytes.fromhex("01")

        with pytest.raises(SwitchbotOperationError):
            await device.get_time_offset()

    @pytest.mark.asyncio
    async def test_set_time_offset_positive(self):
        device = self.create_device()
        device._send_command.return_value = bytes.fromhex("01")

        await device.set_time_offset(1055689)
        device._send_command.assert_called_with("570f68050600101bc9")

    @pytest.mark.asyncio
    async def test_set_time_offset_negative(self):
        device = self.create_device()
        device._send_command.return_value = bytes.fromhex("01")

        await device.set_time_offset(-4096)
        device._send_command.assert_called_with("570f68050680001000")

    @pytest.mark.asyncio
    async def test_set_time_offset_too_large(self):
        device = self.create_device()
        max_offset = SwitchbotMeterProCO2.MAX_TIME_OFFSET

        with pytest.raises(SwitchbotOperationError):
            await device.set_time_offset(max_offset + 1)

        with pytest.raises(SwitchbotOperationError):
            await device.set_time_offset(-(max_offset + 1))

    @pytest.mark.asyncio
    async def test_set_time_offset_failure(self):
        device = self.create_device()
        device._send_command.return_value = bytes.fromhex("00")

        with pytest.raises(SwitchbotOperationError):
            await device.set_time_offset(100)
