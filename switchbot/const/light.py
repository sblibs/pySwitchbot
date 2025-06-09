from enum import Enum


class ColorMode(Enum):
    OFF = 0
    COLOR_TEMP = 1
    RGB = 2
    EFFECT = 3


class StripLightColorMode(Enum):
    RGB = 2
    SCENE = 3
    MUSIC = 4
    CONTROLLER = 5
    COLOR_TEMP = 6
    UNKNOWN = 10


class BulbColorMode(Enum):
    COLOR_TEMP = 1
    RGB = 2
    DYNAMIC = 3
    UNKNOWN = 10


class CeilingLightColorMode(Enum):
    COLOR_TEMP = 0
    NIGHT = 1
    MUSIC = 4
    UNKNOWN = 10


# Mappings from device-specific color modes to original ColorMode enum
STRIP_LIGHT_COLOR_MODE_MAP = {
    StripLightColorMode.RGB: ColorMode.RGB,
    StripLightColorMode.SCENE: ColorMode.EFFECT,
    StripLightColorMode.MUSIC: ColorMode.EFFECT,
    StripLightColorMode.CONTROLLER: ColorMode.EFFECT,
    StripLightColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    StripLightColorMode.UNKNOWN: ColorMode.OFF,
}

BULB_COLOR_MODE_MAP = {
    BulbColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    BulbColorMode.RGB: ColorMode.RGB,
    BulbColorMode.DYNAMIC: ColorMode.EFFECT,
    BulbColorMode.UNKNOWN: ColorMode.OFF,
}

CEILING_LIGHT_COLOR_MODE_MAP = {
    CeilingLightColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
    CeilingLightColorMode.NIGHT: ColorMode.COLOR_TEMP,
    CeilingLightColorMode.MUSIC: ColorMode.EFFECT,
    CeilingLightColorMode.UNKNOWN: ColorMode.OFF,
}


DEFAULT_COLOR_TEMP = 4001
