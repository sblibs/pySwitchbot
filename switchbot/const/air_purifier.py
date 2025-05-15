from __future__ import annotations

from enum import Enum


class AirPurifierMode(Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    AUTO = 4
    SLEEP = 5
    PET = 6

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.name.lower() for mode in cls]


class AirQualityLevel(Enum):
    EXCELLENT = 0
    GOOD = 1
    MODERATE = 2
    UNHEALTHY = 3
