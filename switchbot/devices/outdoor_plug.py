from typing import Any

from ..const import SwitchbotModel
from ..models import SwitchBotAdvertisement
from .relay_switch import COMMAND_GET_CHANNEL2_INFO, SwitchbotRelaySwitch


class SwitchbotOutdoorPlug(SwitchbotRelaySwitch):
    """An Outdoor Plug EU with bidirectional metering."""

    _model = SwitchbotModel.OUTDOOR_PLUG_EU

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Preserve polled metering values alongside advertised power."""
        data = advertisement.data["data"]
        for key in (
            "voltage",
            "current",
            "energy",
            "current_production",
            "energy_production",
        ):
            data[key] = self._get_adv_value(key) or 0
        super().update_from_advertisement(advertisement)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Read consumption and production for the single relay."""
        if not (data := await super().get_basic_info()):
            return None
        now, day_start = self.get_current_time_and_start_time()
        raw = await self._get_basic_info(
            COMMAND_GET_CHANNEL2_INFO.format(now, day_start)
        )
        if not raw or len(raw) < 15:
            return None
        production = self._parse_user_data(raw)
        if not data["isOn"]:
            self._reset_power_data(production)
        return data | {
            "power_production": production["power"],
            "current_production": production["current"],
            "energy_production": production["energy"],
        }
