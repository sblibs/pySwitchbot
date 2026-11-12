"""Device handler for Art Frame Luma."""

from ..const import SwitchbotModel
from .image_frame import SwitchbotImageFrame


class SwitchbotArtFrameLuma(SwitchbotImageFrame):
    """Represent a Art Frame Luma."""

    _model = SwitchbotModel.ART_FRAME_LUMA
