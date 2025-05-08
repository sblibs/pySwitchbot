"""Switchbot Device Consts Library."""

from __future__ import annotations

from ..enum import StrEnum
from .fan import FanMode

# Preserve old LockStatus export for backwards compatibility
from .lock import LockStatus

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5


class SwitchbotApiError(RuntimeError):
    """
    Raised when API call fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class SwitchbotAuthenticationError(RuntimeError):
    """
    Raised when authentication fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class SwitchbotAccountConnectionError(RuntimeError):
    """
    Raised when connection to Switchbot account fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class SwitchbotModel(StrEnum):
    BOT = "WoHand"
    CURTAIN = "WoCurtain"
    HUMIDIFIER = "WoHumi"
    PLUG_MINI = "WoPlug"
    CONTACT_SENSOR = "WoContact"
    LIGHT_STRIP = "WoStrip"
    METER = "WoSensorTH"
    METER_PRO = "WoTHP"
    METER_PRO_C = "WoTHPc"
    IO_METER = "WoIOSensorTH"
    MOTION_SENSOR = "WoPresence"
    COLOR_BULB = "WoBulb"
    CEILING_LIGHT = "WoCeiling"
    LOCK = "WoLock"
    LOCK_PRO = "WoLockPro"
    BLIND_TILT = "WoBlindTilt"
    HUB2 = "WoHub2"
    LEAK = "Leak Detector"
    KEYPAD = "WoKeypad"
    RELAY_SWITCH_1PM = "Relay Switch 1PM"
    RELAY_SWITCH_1 = "Relay Switch 1"
    REMOTE = "WoRemote"
    EVAPORATIVE_HUMIDIFIER = "Evaporative Humidifier"
    ROLLER_SHADE = "Roller Shade"
    HUBMINI_MATTER = "HubMini Matter"
    CIRCULATOR_FAN = "Circulator Fan"
    K20_VACUUM = "K20 Vacuum"
    S10_VACUUM = "S10 Vacuum"
    K10_VACUUM = "K10+ Vacuum"
    K10_PRO_VACUUM = "K10+ Pro Vacuum"
    K10_PRO_COMBO_VACUUM = "K10+ Pro Combo Vacuum"


__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "FanMode",
    "LockStatus",
    "SwitchbotAccountConnectionError",
    "SwitchbotApiError",
    "SwitchbotAuthenticationError",
    "SwitchbotModel",
]
