from __future__ import annotations

from enum import Enum


class FanMode(Enum):
    NORMAL = 1
    NATURAL = 2
    SLEEP = 3
    BABY = 4

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.name.lower() for mode in cls]


class StandingFanMode(Enum):
    NORMAL = 1
    NATURAL = 2
    SLEEP = 3
    BABY = 4
    CUSTOM_NATURAL = 5

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.name.lower() for mode in cls]


class NightLightState(Enum):
    """Standing Fan night-light command values."""

    LEVEL_1 = 1
    LEVEL_2 = 2
    OFF = 3


class OscillationAngle(Enum):
    """Standing Fan oscillation angle command values (degrees)."""

    ANGLE_30 = 30
    ANGLE_60 = 60
    ANGLE_90 = 90
