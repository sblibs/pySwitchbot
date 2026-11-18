from enum import Enum


class MeterProWeatherIcon(Enum):
    """Weather icons supported by the Meter Pro and Meter Pro CO2 displays."""

    NONE = 0
    SUNNY = 1
    CLOUDY = 2
    OVERCAST = 3
    LIGHT_RAIN = 4
    HEAVY_RAIN = 5
    LIGHT_SNOW = 6
    HEAVY_SNOW = 7


class MeterProDisplayZone(Enum):
    """Configurable areas of the Meter Pro screen."""

    MIDDLE = 1
    BOTTOM = 2


class MeterProZoneIcon(Enum):
    """Icon shown next to a display zone."""

    INDOOR = 1
    OUTDOOR = 2


class MeterProDisplaySource(Enum):
    """Where a display zone takes its temperature and humidity from."""

    NONE = 0
    METER = 1
    METER_PLUS = 2
    INDOOR_OUTDOOR_METER = 3
    HUB = 4  # Hub 2 and Hub Mini Matter
    METER_PRO = 5  # this device when the MAC is empty, else another Meter Pro
    NETWORK = 6  # values written with the weather command
    WEATHER_STATION = 8
    HUB3 = 9


class MeterProDateFormat(Enum):
    """Date layout on the screen."""

    MONTH_DAY = 0
    DAY_MONTH = 1
