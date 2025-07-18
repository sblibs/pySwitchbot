"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypedDict

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parsers.air_purifier import process_air_purifier
from .adv_parsers.blind_tilt import process_woblindtilt
from .adv_parsers.bot import process_wohand
from .adv_parsers.bulb import process_color_bulb
from .adv_parsers.ceiling_light import process_woceiling
from .adv_parsers.contact import process_wocontact
from .adv_parsers.curtain import process_wocurtain
from .adv_parsers.fan import process_fan
from .adv_parsers.hub2 import process_wohub2
from .adv_parsers.hub3 import process_hub3
from .adv_parsers.hubmini_matter import process_hubmini_matter
from .adv_parsers.humidifier import process_evaporative_humidifier, process_wohumidifier
from .adv_parsers.keypad import process_wokeypad
from .adv_parsers.leak import process_leak
from .adv_parsers.light_strip import process_light, process_wostrip
from .adv_parsers.lock import (
    process_lock2,
    process_locklite,
    process_wolock,
    process_wolock_pro,
)
from .adv_parsers.meter import process_wosensorth, process_wosensorth_c
from .adv_parsers.motion import process_wopresence
from .adv_parsers.plug import process_woplugmini
from .adv_parsers.relay_switch import (
    process_garage_door_opener,
    process_relay_switch_2pm,
    process_relay_switch_common_data,
)
from .adv_parsers.remote import process_woremote
from .adv_parsers.roller_shade import process_worollershade
from .adv_parsers.vacuum import process_vacuum, process_vacuum_k
from .const import SwitchbotModel
from .models import SwitchBotAdvertisement

_LOGGER = logging.getLogger(__name__)

SERVICE_DATA_ORDER = (
    "0000fd3d-0000-1000-8000-00805f9b34fb",
    "00000d00-0000-1000-8000-00805f9b34fb",
)
MFR_DATA_ORDER = (2409, 741, 89)


class SwitchbotSupportedType(TypedDict):
    """Supported type of Switchbot."""

    modelName: SwitchbotModel
    modelFriendlyName: str
    func: Callable[[bytes, bytes | None], dict[str, bool | int]]
    manufacturer_id: int | None
    manufacturer_data_length: int | None


SUPPORTED_TYPES: dict[str | bytes, SwitchbotSupportedType] = {
    "d": {
        "modelName": SwitchbotModel.CONTACT_SENSOR,
        "modelFriendlyName": "Contact Sensor",
        "func": process_wocontact,
        "manufacturer_id": 2409,
    },
    "H": {
        "modelName": SwitchbotModel.BOT,
        "modelFriendlyName": "Bot",
        "func": process_wohand,
        "manufacturer_id": 89,
    },
    "s": {
        "modelName": SwitchbotModel.MOTION_SENSOR,
        "modelFriendlyName": "Motion Sensor",
        "func": process_wopresence,
        "manufacturer_id": 2409,
    },
    "r": {
        "modelName": SwitchbotModel.LIGHT_STRIP,
        "modelFriendlyName": "Light Strip",
        "func": process_wostrip,
        "manufacturer_id": 2409,
    },
    "{": {
        "modelName": SwitchbotModel.CURTAIN,
        "modelFriendlyName": "Curtain 3",
        "func": process_wocurtain,
        "manufacturer_id": 2409,
    },
    "c": {
        "modelName": SwitchbotModel.CURTAIN,
        "modelFriendlyName": "Curtain",
        "func": process_wocurtain,
        "manufacturer_id": 2409,
    },
    "w": {
        "modelName": SwitchbotModel.IO_METER,
        "modelFriendlyName": "Indoor/Outdoor Meter",
        "func": process_wosensorth,
        "manufacturer_id": 2409,
    },
    "i": {
        "modelName": SwitchbotModel.METER,
        "modelFriendlyName": "Meter Plus",
        "func": process_wosensorth,
        "manufacturer_id": 2409,
    },
    "T": {
        "modelName": SwitchbotModel.METER,
        "modelFriendlyName": "Meter",
        "func": process_wosensorth,
        "manufacturer_id": 2409,
    },
    "4": {
        "modelName": SwitchbotModel.METER_PRO,
        "modelFriendlyName": "Meter Pro",
        "func": process_wosensorth,
        "manufacturer_id": 2409,
    },
    "5": {
        "modelName": SwitchbotModel.METER_PRO_C,
        "modelFriendlyName": "Meter Pro CO2",
        "func": process_wosensorth_c,
        "manufacturer_id": 2409,
    },
    "v": {
        "modelName": SwitchbotModel.HUB2,
        "modelFriendlyName": "Hub 2",
        "func": process_wohub2,
        "manufacturer_id": 2409,
    },
    "g": {
        "modelName": SwitchbotModel.PLUG_MINI,
        "modelFriendlyName": "Plug Mini",
        "func": process_woplugmini,
        "manufacturer_id": 2409,
    },
    "j": {
        "modelName": SwitchbotModel.PLUG_MINI,
        "modelFriendlyName": "Plug Mini (JP)",
        "func": process_woplugmini,
        "manufacturer_id": 2409,
    },
    "u": {
        "modelName": SwitchbotModel.COLOR_BULB,
        "modelFriendlyName": "Color Bulb",
        "func": process_color_bulb,
        "manufacturer_id": 2409,
    },
    "q": {
        "modelName": SwitchbotModel.CEILING_LIGHT,
        "modelFriendlyName": "Ceiling Light",
        "func": process_woceiling,
        "manufacturer_id": 2409,
    },
    "n": {
        "modelName": SwitchbotModel.CEILING_LIGHT,
        "modelFriendlyName": "Ceiling Light Pro",
        "func": process_woceiling,
        "manufacturer_id": 2409,
    },
    "e": {
        "modelName": SwitchbotModel.HUMIDIFIER,
        "modelFriendlyName": "Humidifier",
        "func": process_wohumidifier,
        "manufacturer_id": 741,
        "manufacturer_data_length": 6,
    },
    "#": {
        "modelName": SwitchbotModel.EVAPORATIVE_HUMIDIFIER,
        "modelFriendlyName": "Evaporative Humidifier",
        "func": process_evaporative_humidifier,
        "manufacturer_id": 2409,
    },
    "o": {
        "modelName": SwitchbotModel.LOCK,
        "modelFriendlyName": "Lock",
        "func": process_wolock,
        "manufacturer_id": 2409,
    },
    "$": {
        "modelName": SwitchbotModel.LOCK_PRO,
        "modelFriendlyName": "Lock Pro",
        "func": process_wolock_pro,
        "manufacturer_id": 2409,
    },
    "x": {
        "modelName": SwitchbotModel.BLIND_TILT,
        "modelFriendlyName": "Blind Tilt",
        "func": process_woblindtilt,
        "manufacturer_id": 2409,
    },
    "&": {
        "modelName": SwitchbotModel.LEAK,
        "modelFriendlyName": "Leak Detector",
        "func": process_leak,
        "manufacturer_id": 2409,
    },
    "y": {
        "modelName": SwitchbotModel.KEYPAD,
        "modelFriendlyName": "Keypad",
        "func": process_wokeypad,
        "manufacturer_id": 2409,
    },
    "<": {
        "modelName": SwitchbotModel.RELAY_SWITCH_1PM,
        "modelFriendlyName": "Relay Switch 1PM",
        "func": process_relay_switch_common_data,
        "manufacturer_id": 2409,
    },
    ";": {
        "modelName": SwitchbotModel.RELAY_SWITCH_1,
        "modelFriendlyName": "Relay Switch 1",
        "func": process_relay_switch_common_data,
        "manufacturer_id": 2409,
    },
    "b": {
        "modelName": SwitchbotModel.REMOTE,
        "modelFriendlyName": "Remote",
        "func": process_woremote,
        "manufacturer_id": 89,
    },
    ",": {
        "modelName": SwitchbotModel.ROLLER_SHADE,
        "modelFriendlyName": "Roller Shade",
        "func": process_worollershade,
        "manufacturer_id": 2409,
    },
    "%": {
        "modelName": SwitchbotModel.HUBMINI_MATTER,
        "modelFriendlyName": "HubMini Matter",
        "func": process_hubmini_matter,
        "manufacturer_id": 2409,
    },
    "~": {
        "modelName": SwitchbotModel.CIRCULATOR_FAN,
        "modelFriendlyName": "Circulator Fan",
        "func": process_fan,
        "manufacturer_id": 2409,
    },
    ".": {
        "modelName": SwitchbotModel.K20_VACUUM,
        "modelFriendlyName": "K20 Vacuum",
        "func": process_vacuum,
        "manufacturer_id": 2409,
    },
    "z": {
        "modelName": SwitchbotModel.S10_VACUUM,
        "modelFriendlyName": "S10 Vacuum",
        "func": process_vacuum,
        "manufacturer_id": 2409,
    },
    "3": {
        "modelName": SwitchbotModel.K10_PRO_COMBO_VACUUM,
        "modelFriendlyName": "K10+ Pro Combo Vacuum",
        "func": process_vacuum,
        "manufacturer_id": 2409,
    },
    "}": {
        "modelName": SwitchbotModel.K10_VACUUM,
        "modelFriendlyName": "K10+ Vacuum",
        "func": process_vacuum_k,
        "manufacturer_id": 2409,
    },
    "(": {
        "modelName": SwitchbotModel.K10_PRO_VACUUM,
        "modelFriendlyName": "K10+ Pro Vacuum",
        "func": process_vacuum_k,
        "manufacturer_id": 2409,
    },
    "*": {
        "modelName": SwitchbotModel.AIR_PURIFIER,
        "modelFriendlyName": "Air Purifier",
        "func": process_air_purifier,
        "manufacturer_id": 2409,
    },
    "+": {
        "modelName": SwitchbotModel.AIR_PURIFIER,
        "modelFriendlyName": "Air Purifier",
        "func": process_air_purifier,
        "manufacturer_id": 2409,
    },
    "7": {
        "modelName": SwitchbotModel.AIR_PURIFIER_TABLE,
        "modelFriendlyName": "Air Purifier Table",
        "func": process_air_purifier,
        "manufacturer_id": 2409,
    },
    "8": {
        "modelName": SwitchbotModel.AIR_PURIFIER_TABLE,
        "modelFriendlyName": "Air Purifier Table",
        "func": process_air_purifier,
        "manufacturer_id": 2409,
    },
    b"\x00\x10\xb9\x40": {
        "modelName": SwitchbotModel.HUB3,
        "modelFriendlyName": "Hub3",
        "func": process_hub3,
        "manufacturer_id": 2409,
    },
    "-": {
        "modelName": SwitchbotModel.LOCK_LITE,
        "modelFriendlyName": "Lock Lite",
        "func": process_locklite,
        "manufacturer_id": 2409,
    },
    b"\x00\x10\xa5\xb8": {
        "modelName": SwitchbotModel.LOCK_ULTRA,
        "modelFriendlyName": "Lock Ultra",
        "func": process_lock2,
        "manufacturer_id": 2409,
    },
    ">": {
        "modelName": SwitchbotModel.GARAGE_DOOR_OPENER,
        "modelFriendlyName": "Garage Door Opener",
        "func": process_garage_door_opener,
        "manufacturer_id": 2409,
    },
    "=": {
        "modelName": SwitchbotModel.RELAY_SWITCH_2PM,
        "modelFriendlyName": "Relay Switch 2PM",
        "func": process_relay_switch_2pm,
        "manufacturer_id": 2409,
    },
    b"\x00\x10\xd0\xb0": {
        "modelName": SwitchbotModel.FLOOR_LAMP,
        "modelFriendlyName": "Floor Lamp",
        "func": process_light,
        "manufacturer_id": 2409,
    },
    b"\x00\x10\xd0\xb1": {
        "modelName": SwitchbotModel.STRIP_LIGHT_3,
        "modelFriendlyName": "Strip Light 3",
        "func": process_light,
        "manufacturer_id": 2409,
    },
}

_SWITCHBOT_MODEL_TO_CHAR = {
    model_data["modelName"]: model_chr
    for model_chr, model_data in SUPPORTED_TYPES.items()
}

MODELS_BY_MANUFACTURER_DATA: dict[int, list[tuple[str, SwitchbotSupportedType]]] = {
    mfr_id: [] for mfr_id in MFR_DATA_ORDER
}
for model_chr, model in SUPPORTED_TYPES.items():
    if "manufacturer_id" in model:
        mfr_id = model["manufacturer_id"]
        MODELS_BY_MANUFACTURER_DATA[mfr_id].append((model_chr, model))


def parse_advertisement_data(
    device: BLEDevice,
    advertisement_data: AdvertisementData,
    model: SwitchbotModel | None = None,
) -> SwitchBotAdvertisement | None:
    """Parse advertisement data."""
    service_data = advertisement_data.service_data

    _service_data = None
    for uuid in SERVICE_DATA_ORDER:
        if uuid in service_data:
            _service_data = service_data[uuid]
            break

    _mfr_data = None
    _mfr_id = None
    for mfr_id in MFR_DATA_ORDER:
        if mfr_id in advertisement_data.manufacturer_data:
            _mfr_id = mfr_id
            _mfr_data = advertisement_data.manufacturer_data[mfr_id]
            break

    if _mfr_data is None and _service_data is None:
        return None

    try:
        data = _parse_data(
            _service_data,
            _mfr_data,
            _mfr_id,
            model,
        )
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Failed to parse advertisement data: %s", advertisement_data)
        return None

    if not data:
        return None

    return SwitchBotAdvertisement(
        device.address, data, device, advertisement_data.rssi, bool(_service_data)
    )


@lru_cache(maxsize=128)
def _parse_data(
    _service_data: bytes | None,
    _mfr_data: bytes | None,
    _mfr_id: int | None = None,
    _switchbot_model: SwitchbotModel | None = None,
) -> dict[str, Any] | None:
    """Parse advertisement data."""
    _model = chr(_service_data[0] & 0b01111111) if _service_data else None

    if _switchbot_model and _switchbot_model in _SWITCHBOT_MODEL_TO_CHAR:
        _model = _SWITCHBOT_MODEL_TO_CHAR[_switchbot_model]

    if not _model and _mfr_id and _mfr_id in MODELS_BY_MANUFACTURER_DATA:
        for model_chr, model_data in MODELS_BY_MANUFACTURER_DATA[_mfr_id]:
            if model_data.get("manufacturer_data_length") == len(_mfr_data):
                _model = model_chr
                break
    if (
        _service_data
        and len(_service_data) > 5
        and _service_data[-4:] in SUPPORTED_TYPES
    ):
        _model = _service_data[-4:]

    if not _model:
        return None

    _isEncrypted = bool(_service_data[0] & 0b10000000) if _service_data else False
    data = {
        "rawAdvData": _service_data,
        "data": {},
        "model": _model,
        "isEncrypted": _isEncrypted,
    }

    type_data = SUPPORTED_TYPES.get(_model)
    if type_data:
        model_data = type_data["func"](_service_data, _mfr_data)
        if model_data:
            data.update(
                {
                    "modelFriendlyName": type_data["modelFriendlyName"],
                    "modelName": type_data["modelName"],
                    "data": model_data,
                }
            )

    return data
