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
    BulbColorMode,
    CeilingLightColorMode,
    ClimateAction,
    ClimateMode,
    ColorMode,
    FanMode,
    HumidifierAction,
    HumidifierMode,
    HumidifierWaterLevel,
    LockStatus,
    SmartThermostatRadiatorMode,
    StripLightColorMode,
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
from .devices.device import (
    SwitchbotDevice,
    SwitchbotEncryptedDevice,
    SwitchbotOperationError,
    fetch_cloud_devices,
)
from .devices.evaporative_humidifier import SwitchbotEvaporativeHumidifier
from .devices.fan import SwitchbotFan
from .devices.humidifier import SwitchbotHumidifier
from .devices.light_strip import (
    SwitchbotLightStrip,
    SwitchbotRgbicLight,
    SwitchbotStripLight3,
)
from .devices.lock import SwitchbotLock
from .devices.plug import SwitchbotPlugMini
from .devices.relay_switch import (
    SwitchbotGarageDoorOpener,
    SwitchbotRelaySwitch,
    SwitchbotRelaySwitch2PM,
)
from .devices.roller_shade import SwitchbotRollerShade
from .devices.smart_thermostat_radiator import SwitchbotSmartThermostatRadiator
from .devices.vacuum import SwitchbotVacuum
from .discovery import GetSwitchbotDevices
from .models import SwitchBotAdvertisement

__all__ = [
    "AirPurifierMode",
    "BulbColorMode",
    "CeilingLightColorMode",
    "ClimateAction",
    "ClimateMode",
    "ColorMode",
    "FanMode",
    "GetSwitchbotDevices",
    "HumidifierAction",
    "HumidifierMode",
    "HumidifierWaterLevel",
    "LockStatus",
    "SmartThermostatRadiatorMode",
    "StripLightColorMode",
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
    "SwitchbotGarageDoorOpener",
    "SwitchbotHumidifier",
    "SwitchbotLightStrip",
    "SwitchbotLock",
    "SwitchbotModel",
    "SwitchbotModel",
    "SwitchbotOperationError",
    "SwitchbotPlugMini",
    "SwitchbotPlugMini",
    "SwitchbotRelaySwitch",
    "SwitchbotRelaySwitch2PM",
    "SwitchbotRgbicLight",
    "SwitchbotRollerShade",
    "SwitchbotSmartThermostatRadiator",
    "SwitchbotStripLight3",
    "SwitchbotSupportedType",
    "SwitchbotSupportedType",
    "SwitchbotVacuum",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "fetch_cloud_devices",
    "get_device",
    "parse_advertisement_data",
]
