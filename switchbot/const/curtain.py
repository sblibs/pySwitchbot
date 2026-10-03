"""Curtain diagnostic states."""

from __future__ import annotations

from ..enum import StrEnum


class CurtainChargingState(StrEnum):
    NOT_CHARGING = "not_charging"
    CHARGING_BY_ADAPTER = "charging_by_adapter"
    CHARGING_BY_SOLAR = "charging_by_solar"
    ADAPTER_FULL = "adapter_full"
    SOLAR_FULL = "solar_full"
    SOLAR_NOT_CHARGING = "solar_not_charging"
    HARDWARE_ERROR = "hardware_error"


CURTAIN_CHARGING_STATES = dict(enumerate(CurtainChargingState))
