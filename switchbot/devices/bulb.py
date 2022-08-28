from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any

from switchbot.models import SwitchBotAdvertisement

from .device import SwitchbotDevice, SwitchbotSequenceDevice

REQ_HEADER = "570f"
BULB_COMMMAND_HEADER = "4701"
BULB_REQUEST = f"{REQ_HEADER}4801"

BULB_COMMAND = f"{REQ_HEADER}{BULB_COMMMAND_HEADER}"
# Bulb keys
BULB_ON_KEY = f"{BULB_COMMAND}01"
BULB_OFF_KEY = f"{BULB_COMMAND}02"
RGB_BRIGHTNESS_KEY = f"{BULB_COMMAND}12"
CW_BRIGHTNESS_KEY = f"{BULB_COMMAND}13"
BRIGHTNESS_KEY = f"{BULB_COMMAND}14"
RGB_KEY = f"{BULB_COMMAND}16"
CW_KEY = f"{BULB_COMMAND}17"

_LOGGER = logging.getLogger(__name__)

from .base_light import SwitchbotBaseLight
from .device import ColorMode


class SwitchbotBulb(SwitchbotBaseLight):
    """Representation of a Switchbot bulb."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot bulb constructor."""
        super().__init__(*args, **kwargs)
        self._state: dict[str, Any] = {}

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB, ColorMode.COLOR_TEMP}

    async def update(self) -> None:
        """Update state of device."""
        result = await self._sendcommand(BULB_REQUEST)
        self._update_state(result)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._sendcommand(BULB_ON_KEY)
        self._update_state(result)
        return self._check_command_result(result, 1, {0x80})

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._sendcommand(BULB_OFF_KEY)
        self._update_state(result)
        return self._check_command_result(result, 1, {0x00})

    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        result = await self._sendcommand(f"{BRIGHTNESS_KEY}{brightness:02X}")
        self._update_state(result)
        return self._check_command_result(result, 1, {0x80})

    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 2700 <= color_temp <= 6500, "Color Temp must be between 0 and 100"
        result = await self._sendcommand(
            f"{CW_BRIGHTNESS_KEY}{brightness:02X}{color_temp:04X}"
        )
        self._update_state(result)
        return self._check_command_result(result, 1, {0x80})

    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 0 <= r <= 255, "r must be between 0 and 255"
        assert 0 <= g <= 255, "g must be between 0 and 255"
        assert 0 <= b <= 255, "b must be between 0 and 255"
        result = await self._sendcommand(
            f"{RGB_BRIGHTNESS_KEY}{brightness:02X}{r:02X}{g:02X}{b:02X}"
        )
        self._update_state(result)
        return self._check_command_result(result, 1, {0x80})

    def _update_state(self, result: bytes | None) -> None:
        """Update device state."""
        if not result or len(result) < 10:
            return
        self._state["r"] = result[3]
        self._state["g"] = result[4]
        self._state["b"] = result[5]
        self._state["cw"] = int(result[6:8].hex(), 16)
        _LOGGER.debug(
            "%s: Bulb update state: %s = %s", self.name, result.hex(), self._state
        )
        self._fire_callbacks()
