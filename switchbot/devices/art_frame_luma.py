"""Device handler for Art Frame Luma."""

from ..const import SwitchbotModel
from .art_frame2 import SwitchbotArtFrame2


class SwitchbotArtFrameLuma(SwitchbotArtFrame2):
    """Represent a Art Frame Luma."""

    _model = SwitchbotModel.ART_FRAME_LUMA
