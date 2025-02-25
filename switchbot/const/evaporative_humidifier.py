from __future__ import annotations

from enum import Enum


class HumidifierMode(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    QUIET = 4
    TARGET_HUMIDITY = 5
    SLEEP = 6
    AUTO = 7
    DRYING_FILTER = 8


class HumidifierWaterLevel(Enum):
    EMPTY = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


OVER_HUMIDIFY_PROTECTION_MODES = {
    HumidifierMode.QUIET,
    HumidifierMode.LOW,
    HumidifierMode.MEDIUM,
    HumidifierMode.HIGH,
}

TARGET_HUMIDITY_MODES = {
    HumidifierMode.SLEEP,
    HumidifierMode.TARGET_HUMIDITY,
}
