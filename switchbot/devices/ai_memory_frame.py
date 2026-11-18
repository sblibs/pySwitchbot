"""Device handler for E Ink Photo Magnet."""

from ..const import SwitchbotModel
from .art_frame2 import SwitchbotArtFrame2


class SwitchbotAIMemoryFrame(SwitchbotArtFrame2):
    """Represent an E Ink Photo Magnet."""

    _model = SwitchbotModel.AI_MEMORY_FRAME
