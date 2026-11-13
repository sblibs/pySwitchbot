"""Device handler for Art Frame 2."""

from ..const import SwitchbotModel
from .art_frame2 import SwitchbotArtFrame2


class SwitchbotArtFrameLuma(SwitchbotArtFrame2):
    """Represent an Art Frame 2."""

    _model = SwitchbotModel.ART_FRAME_LUMA
