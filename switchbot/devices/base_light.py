from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from .device import ColorMode, SwitchbotSequenceDevice


class SwitchbotBaseLight(SwitchbotSequenceDevice):
    """Representation of a Switchbot light."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot bulb constructor."""
        super().__init__(*args, **kwargs)
        self._state: dict[str, Any] = {}

    @property
    def on(self) -> bool | None:
        """Return if bulb is on."""
        return self.is_on()

    @property
    def rgb(self) -> tuple[int, int, int] | None:
        """Return the current rgb value."""
        if "r" not in self._state or "g" not in self._state or "b" not in self._state:
            return None
        return self._state["r"], self._state["g"], self._state["b"]

    @property
    def color_temp(self) -> int | None:
        """Return the current color temp value."""
        return self._state.get("cw") or self.min_temp

    @property
    def brightness(self) -> int | None:
        """Return the current brightness value."""
        return self._get_adv_value("brightness") or 0

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        return ColorMode(self._get_adv_value("color_mode") or 0)

    @property
    def min_temp(self) -> int:
        """Return minimum color temp."""
        return 2700

    @property
    def max_temp(self) -> int:
        """Return maximum color temp."""
        return 6500

    def is_on(self) -> bool | None:
        """Return bulb state from cache."""
        return self._get_adv_value("isOn")
