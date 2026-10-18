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
    HALF_LOCKED = 7  # Only Lock2 EU lock type


class QuickKeyFunction(Enum):
    """
    Action of the Lock Ultra Quick Key.

    Value is the 2-bit function field of the Quick Key config byte. Lock Ultra.
    """

    LOCK_AND_UNLOCK = 0b10
    UNLOCK_ONLY = 0b01
    LOCK_ONLY = 0b00
