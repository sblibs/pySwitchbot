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

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.name.lower() for mode in cls]


class HumidifierWaterLevel(Enum):
    EMPTY = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def get_levels(cls) -> list[str]:
        return [level.name.lower() for level in cls]


class HumidifierAction(Enum):
    OFF = 0
    HUMIDIFYING = 1
    DRYING = 2


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
