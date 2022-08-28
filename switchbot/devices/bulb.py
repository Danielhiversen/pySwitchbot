from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any

from switchbot.models import SwitchBotAdvertisement

from .device import SwitchbotDevice

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


class ColorMode(Enum):

    OFF = 0
    COLOR_TEMP = 1
    RGB = 2
    EFFECT = 3


class SwitchbotBulb(SwitchbotDevice):
    """Representation of a Switchbot bulb."""

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

    async def update(self) -> None:
        """Update state of device."""
        result = await self._sendcommand(BULB_REQUEST)
        self._update_state(result)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._sendcommand(BULB_ON_KEY)
        self._update_state(result)
        return result[1] == 0x80

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._sendcommand(BULB_OFF_KEY)
        self._update_state(result)
        return result[1] == 0x00

    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        result = await self._sendcommand(f"{BRIGHTNESS_KEY}{brightness:02X}")
        self._update_state(result)
        return result[1] == 0x80

    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 2700 <= color_temp <= 6500, "Color Temp must be between 0 and 100"
        result = await self._sendcommand(
            f"{CW_BRIGHTNESS_KEY}{brightness:02X}{color_temp:04X}"
        )
        self._update_state(result)
        return result[1] == 0x80

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
        return result[1] == 0x80

    def is_on(self) -> bool | None:
        """Return bulb state from cache."""
        return self._get_adv_value("isOn")

    def _update_state(self, result: bytes) -> None:
        """Update device state."""
        if len(result) < 10:
            return
        self._state["r"] = result[3]
        self._state["g"] = result[4]
        self._state["b"] = result[5]
        self._state["cw"] = int(result[6:8].hex(), 16)
        _LOGGER.debug(
            "%s: Bulb update state: %s = %s", self.name, result.hex(), self._state
        )
        self._fire_callbacks()

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        current_state = self._get_adv_value("sequence_number")
        super().update_from_advertisement(advertisement)
        new_state = self._get_adv_value("sequence_number")
        _LOGGER.debug(
            "%s: Bulb update advertisement: %s (seq before: %s) (seq after: %s)",
            self.name,
            advertisement,
            current_state,
            new_state,
        )
        if current_state != new_state:
            asyncio.ensure_future(self.update())
