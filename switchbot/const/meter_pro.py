from enum import Enum


class MeterProWeatherIcon(Enum):
    """Weather icons supported by the Meter Pro CO2 display."""

    NONE = 0
    SUNNY = 1
    PARTLY_CLOUDY = 2
    CLOUDY = 3
    RAINY = 4
    POURING = 5
    SNOWY = 6
    HEAVY_SNOW = 7
