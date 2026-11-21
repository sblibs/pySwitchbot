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


# Wire codes are listed explicitly so reordering the enum can't change decoding.
CURTAIN_CHARGING_STATES = {
    0: CurtainChargingState.NOT_CHARGING,
    1: CurtainChargingState.CHARGING_BY_ADAPTER,
    2: CurtainChargingState.CHARGING_BY_SOLAR,
    3: CurtainChargingState.ADAPTER_FULL,
    4: CurtainChargingState.SOLAR_FULL,
    5: CurtainChargingState.SOLAR_NOT_CHARGING,
    6: CurtainChargingState.HARDWARE_ERROR,
}

# The stateOfCharge strings reported before chargingState was added.
LEGACY_STATE_OF_CHARGE = {
    CurtainChargingState.ADAPTER_FULL: "fully_charged",
    CurtainChargingState.SOLAR_FULL: "fully_charged",
    CurtainChargingState.HARDWARE_ERROR: "charging_error",
}
