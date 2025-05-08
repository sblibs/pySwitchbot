"""Library to handle connection with Switchbot."""

from __future__ import annotations

from typing import Any

from .device import SwitchbotSequenceDevice, update_after_operation

COMMAND_CLEAN_UP = {
    1: "570F5A00FFFF7001",
    2: "5A400101010126",
}
COMMAND_RETURN_DOCK = {
    1: "570F5A00FFFF7002",
    2: "5A400101010225",
}


class SwitchbotVacuum(SwitchbotSequenceDevice):
    """Representation of a Switchbot Vacuum."""

    def __init__(self, device, password=None, interface=0, **kwargs):
        super().__init__(device, password, interface, **kwargs)

    @update_after_operation
    async def clean_up(self, protocol_version: int) -> bool:
        """Send command to perform a spot clean-up."""
        return await self._send_command(COMMAND_CLEAN_UP[protocol_version])

    @update_after_operation
    async def return_to_dock(self, protocol_version: int) -> bool:
        """Send command to return the dock."""
        return await self._send_command(COMMAND_RETURN_DOCK[protocol_version])

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Only support get the ble version through the command."""
        if not (_data := await self._get_basic_info()):
            return None
        return {
            "firmware": _data[2],
        }

    def get_soc_version(self) -> str:
        """Return device soc version."""
        return self._get_adv_value("soc_version")

    def get_last_step(self) -> int:
        """Return device last step after network configuration."""
        return self._get_adv_value("step")

    def get_mqtt_connnect_status(self) -> bool:
        """Return device mqtt connect status."""
        return self._get_adv_value("mqtt_connected")

    def get_battery(self) -> int:
        """Return device battery."""
        return self._get_adv_value("battery")

    def get_work_status(self) -> int:
        """Return device work status."""
        return self._get_adv_value("work_status")

    def get_dustbin_bound_status(self) -> bool:
        """Return the dustbin bound status"""
        return self._get_adv_value("dustbin_bound")

    def get_dustbin_connnected_status(self) -> bool:
        """Return the dustbin connected status"""
        return self._get_adv_value("dusbin_connected")

    def get_network_connected_status(self) -> bool:
        """Return the network connected status"""
        return self._get_adv_value("network_connected")
