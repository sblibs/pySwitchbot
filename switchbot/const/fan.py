from __future__ import annotations

from enum import Enum


class FanMode(Enum):
    NORMAL = 1
    NATURAL = 2
    SLEEP = 3
    BABY = 4

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.name for mode in cls]
