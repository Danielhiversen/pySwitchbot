from __future__ import annotations

import logging
from typing import Any

from .device import SwitchbotDevice

_LOGGER = logging.getLogger(__name__)


class SwitchbotKeypad(SwitchbotDevice):
    """Representation of a Switchbot keypad."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot keypad constructor."""
        self._lastStatus: list[int] = [-1]
        super().__init__(self._lastStatus, *args, **kwargs)
