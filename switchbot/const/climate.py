"""Representation of climate-related constants."""

from enum import Enum


class ClimateMode:
    """Climate Modes."""

    OFF = 0
    HEAT = 1
    COOL = 2
    HEAT_COOL = 3
    AUTO = 4
    DRY = 5
    FAN_ONLY = 6

class SmartThermostatRadiatorMode(Enum):
    """Smart Thermostat Radiator Modes."""

    AUTO = 0
    MANUAL = 1
    OFF = 2
    ECONOMIC = 3
    COMFORT = 4
    FAST_HEAT = 5

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.name.lower() for mode in cls]

    @classmethod
    def get_mode_name(cls, mode_value: int) -> str:
        try:
            return cls(mode_value)
        except ValueError:
            return cls.OFF
