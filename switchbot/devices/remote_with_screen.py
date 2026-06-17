"""Library to handle connection with Switchbot Remote With Screen."""

from __future__ import annotations

import logging
from typing import Any

from .device import SwitchbotDevice

_LOGGER = logging.getLogger(__name__)


class SwitchbotRemoteWithScreen(SwitchbotDevice):
    """Representation of a Switchbot Remote With Screen (Universal Remote)."""

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        return {
            "battery": _data[1],
            "charging": bool(_data[12]),
        }
