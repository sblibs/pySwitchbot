"""Device handler for AI Memory Frame."""

from ..const import SwitchbotModel
from .art_frame2 import SwitchbotArtFrame2


class SwitchbotAIMemoryFrame(SwitchbotArtFrame2):
    """Represent a AI Memory Frame."""

    _model = SwitchbotModel.AI_MEMORY_FRAME
