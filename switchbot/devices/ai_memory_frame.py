"""Device handler for AI Memory Frame."""

from ..const import SwitchbotModel
from .image_frame import SwitchbotImageFrame


class SwitchbotAIMemoryFrame(SwitchbotImageFrame):
    """Represent a AI Memory Frame."""

    _model = SwitchbotModel.AI_MEMORY_FRAME
