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
