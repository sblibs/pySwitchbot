"""Library to handle connection with Switchbot Universal Remote."""

from __future__ import annotations

import logging
from typing import Any

from .device import SwitchbotDevice

_LOGGER = logging.getLogger(__name__)


class SwitchbotUniversalRemote(SwitchbotDevice):
    """Representation of a Switchbot Universal Remote."""

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        return {
            "battery": _data[1],
            "charging": bool(_data[12]),
        }
