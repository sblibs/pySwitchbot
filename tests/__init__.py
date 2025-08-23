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
