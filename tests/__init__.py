from dataclasses import dataclass

from switchbot import SwitchbotModel


@dataclass
class AdvTestCase:
    manufacturer_data: bytes | None
    service_data: bytes | None
    data: dict
    model: str | bytes
    modelFriendlyName: str
    modelName: SwitchbotModel


STRIP_LIGHT_3_INFO = AdvTestCase(
    b'\xc0N0\xe0U\x9a\x85\x9e"\xd0\x00\x00\x00\x00\x00\x00\x12\x91\x00',
    b"\x00\x00\x00\x00\x10\xd0\xb1",
    {
        "sequence_number": 133,
        "isOn": True,
        "brightness": 30,
        "delay": False,
        "network_state": 2,
        "color_mode": 2,
        "cw": 4753,
    },
    b"\x00\x10\xd0\xb1",
    "Strip Light 3",
    SwitchbotModel.STRIP_LIGHT_3,
)

FLOOR_LAMP_INFO = AdvTestCase(
    b'\xa0\x85\xe3e,\x06P\xaa"\xd4\x00\x00\x00\x00\x00\x00\r\x93\x00',
    b"\x00\x00\x00\x00\x10\xd0\xb0",
    {
        "sequence_number": 80,
        "isOn": True,
        "brightness": 42,
        "delay": False,
        "network_state": 2,
        "color_mode": 2,
        "cw": 3475,
    },
    b"\x00\x10\xd0\xb0",
    "Floor Lamp",
    SwitchbotModel.FLOOR_LAMP,
)

RGBICWW_STRIP_LIGHT_INFO = AdvTestCase(
    b'(7/L\x94\xb2\x0c\x9e"\x00\x11:\x00',
    b"\x00\x00\x00\x00\x10\xd0\xb3",
    {
        "sequence_number": 12,
        "isOn": True,
        "brightness": 30,
        "delay": False,
        "network_state": 2,
        "color_mode": 2,
        "cw": 4410,
    },
    b"\x00\x10\xd0\xb3",
    "Rgbic Strip Light",
    SwitchbotModel.RGBICWW_STRIP_LIGHT,
)

RGBICWW_FLOOR_LAMP_INFO = AdvTestCase(
    b'\xdc\x06u\xa6\xfb\xb2y\x9e"\x00\x11\xb8\x00',
    b"\x00\x00\x00\x00\x10\xd0\xb4",
    {
        "sequence_number": 121,
        "isOn": True,
        "brightness": 30,
        "delay": False,
        "network_state": 2,
        "color_mode": 2,
        "cw": 4536,
    },
    b"\x00\x10\xd0\xb4",
    "Rgbic Floor Lamp",
    SwitchbotModel.RGBICWW_FLOOR_LAMP,
)


SMART_THERMOSTAT_RADIATOR_INFO = AdvTestCase(
    b"\xb0\xe9\xfe\xa2T|6\xe4\x00\x9c\xa3A\x00",
    b"\x00 d\x00\x116@",
    {
        "battery": 100,
        "door_open": False,
        "fault_code": 0,
        "isOn": True,
        "last_mode": "comfort",
        "mode": "manual",
        "sequence_number": 54,
        "need_update_temp": False,
        "restarted": False,
        "target_temperature": 35.0,
        "temperature": 28.0,
    },
    b"\x00\x116@",
    "Smart Thermostat Radiator",
    SwitchbotModel.SMART_THERMOSTAT_RADIATOR,
)


ART_FRAME_INFO = AdvTestCase(
    b"\xb0\xe9\xfe\xe2\xfa8\x157\x03\x08",
    b"\x00\x007\x01\x11>\x10",
    {
        "battery": 55,
        "battery_charging": False,
        "display_mode": 1,
        "display_size": 0,
        "image_index": 3,
        "last_network_status": 0,
        "sequence_number": 21,
    },
    b"\x01\x11>\x10",
    "Art Frame",
    SwitchbotModel.ART_FRAME,
)
