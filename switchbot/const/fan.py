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


class HorizontalOscillationAngle(Enum):
    """
    Horizontal oscillation angle command values.

    For the horizontal axis the device byte is the same as the
    user-facing angle in degrees.
    """

    ANGLE_30 = 30
    ANGLE_60 = 60
    ANGLE_90 = 90


class VerticalOscillationAngle(Enum):
    """
    Vertical oscillation angle command values.

    The Standing Fan uses a different byte encoding on the vertical axis
    than on the horizontal one. Byte 0x5A (decimal 90) is interpreted as
    an axis halt, so 90° maps to byte 0x5F (95). 30° and 60° match their
    degree values.
    """

    ANGLE_30 = 30
    ANGLE_60 = 60
    ANGLE_90 = 95
