"""Library to handle connection with Switchbot."""

import asyncio
from collections.abc import Awaitable
from typing import Any


def execute_task(fut: Awaitable[Any]) -> None:
    """Execute task."""
    task = asyncio.create_task(fut)
    tasks = [task]

    def _cleanup_task(task: asyncio.Task[Any]) -> None:
        """Cleanup task."""
        tasks.remove(task)

    task.add_done_callback(_cleanup_task)
