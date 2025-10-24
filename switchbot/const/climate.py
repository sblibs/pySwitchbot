"""Representation of climate-related constants."""

from enum import Enum


class ClimateMode(Enum):
    """Climate Modes."""

    OFF = 0
    HEAT = 1
    COOL = 2
    HEAT_COOL = 3
    AUTO = 4
    DRY = 5
    FAN_ONLY = 6


class ClimateAction(Enum):
    """Climate Actions."""

    OFF = 0
    IDLE = 1
    HEATING = 2


class SmartThermostatRadiatorMode(Enum):
    """Smart Thermostat Radiator Modes."""

    SCHEDULE = 0
    MANUAL = 1
    OFF = 2
    ECONOMIC = 3
    COMFORT = 4
    FAST_HEATING = 5

    @property
    def lname(self) -> str:
        return self.name.lower()

    @classmethod
    def get_modes(cls) -> list[str]:
        return [mode.lname for mode in cls]

    @classmethod
    def get_mode_name(cls, mode_value: int) -> str:
        return cls(mode_value).lname

    @classmethod
    def get_valid_modes(cls) -> list[str]:
        return [mode.lname for mode in cls if mode != cls.OFF]
