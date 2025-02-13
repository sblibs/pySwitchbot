from __future__ import annotations

from enum import Enum


class LockStatus(Enum):
    LOCKED = 0
    UNLOCKED = 1
    LOCKING = 2
    UNLOCKING = 3
    LOCKING_STOP = 4  # LOCKING_BLOCKED
    UNLOCKING_STOP = 5  # UNLOCKING_BLOCKED
    NOT_FULLY_LOCKED = 6  # LATCH_LOCKED - Only EU lock type
