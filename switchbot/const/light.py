from enum import Enum


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
