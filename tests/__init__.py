from dataclasses import dataclass

from switchbot import SwitchbotModel


@dataclass
class AirPurifierTestCase:
    manufacturer_data: bytes
    service_data: bytes
    data: dict
    model: str
    modelFriendlyName: str
    modelName: SwitchbotModel
