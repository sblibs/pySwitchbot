from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

_R = TypeVar("_R")

_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def create_background_task(target: Coroutine[Any, Any, _R]) -> asyncio.Task[_R]:
    """Create a background task."""
    task = asyncio.create_task(target)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.remove)
    return task
