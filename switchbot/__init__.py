"""Library to handle connection with Switchbot."""

from __future__ import annotations

from bleak_retry_connector import (
    close_stale_connections,
    close_stale_connections_by_address,
    get_device,
)

from .adv_parser import SwitchbotSupportedType, parse_advertisement_data
from .const import (
    AirPurifierMode,
    FanMode,
    LockStatus,
    SwitchbotAccountConnectionError,
    SwitchbotApiError,
    SwitchbotAuthenticationError,
    SwitchbotModel,
)
from .devices.air_purifier import SwitchbotAirPurifier
from .devices.base_light import SwitchbotBaseLight
from .devices.blind_tilt import SwitchbotBlindTilt
from .devices.bot import Switchbot
from .devices.bulb import SwitchbotBulb
from .devices.ceiling_light import SwitchbotCeilingLight
from .devices.curtain import SwitchbotCurtain
from .devices.device import ColorMode, SwitchbotDevice, SwitchbotEncryptedDevice
from .devices.evaporative_humidifier import SwitchbotEvaporativeHumidifier
from .devices.fan import SwitchbotFan
from .devices.humidifier import SwitchbotHumidifier
from .devices.light_strip import SwitchbotLightStrip
from .devices.lock import SwitchbotLock
from .devices.plug import SwitchbotPlugMini
from .devices.relay_switch import SwitchbotRelaySwitch
from .devices.roller_shade import SwitchbotRollerShade
from .devices.vacuum import SwitchbotVacuum
from .discovery import GetSwitchbotDevices
from .models import SwitchBotAdvertisement

__all__ = [
    "AirPurifierMode",
    "ColorMode",
    "FanMode",
    "GetSwitchbotDevices",
    "LockStatus",
    "SwitchBotAdvertisement",
    "Switchbot",
    "Switchbot",
    "SwitchbotAccountConnectionError",
    "SwitchbotAirPurifier",
    "SwitchbotApiError",
    "SwitchbotAuthenticationError",
    "SwitchbotBaseLight",
    "SwitchbotBlindTilt",
    "SwitchbotBulb",
    "SwitchbotCeilingLight",
    "SwitchbotCurtain",
    "SwitchbotDevice",
    "SwitchbotEncryptedDevice",
    "SwitchbotEvaporativeHumidifier",
    "SwitchbotFan",
    "SwitchbotHumidifier",
    "SwitchbotLightStrip",
    "SwitchbotLock",
    "SwitchbotModel",
    "SwitchbotModel",
    "SwitchbotPlugMini",
    "SwitchbotPlugMini",
    "SwitchbotRelaySwitch",
    "SwitchbotRollerShade",
    "SwitchbotSupportedType",
    "SwitchbotSupportedType",
    "SwitchbotVacuum",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "get_device",
    "parse_advertisement_data",
]
