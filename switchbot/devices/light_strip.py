from __future__ import annotations

import logging

from .base_light import SwitchbotSequenceBaseLight
from .device import REQ_HEADER, ColorMode

STRIP_COMMMAND_HEADER = "4901"
STRIP_REQUEST = f"{REQ_HEADER}4A01"

STRIP_COMMAND = f"{REQ_HEADER}{STRIP_COMMMAND_HEADER}"
# Strip keys
STRIP_ON_KEY = f"{STRIP_COMMAND}01"
STRIP_OFF_KEY = f"{STRIP_COMMAND}02"
RGB_BRIGHTNESS_KEY = f"{STRIP_COMMAND}12"
BRIGHTNESS_KEY = f"{STRIP_COMMAND}14"

_LOGGER = logging.getLogger(__name__)


class SwitchbotLightStrip(SwitchbotSequenceBaseLight):
    """Representation of a Switchbot light strip."""

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.RGB}

    async def update(self) -> None:
        """Update state of device."""
        result = await self._send_command(STRIP_REQUEST)
        self._update_state(result)
        await super().update()

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(STRIP_ON_KEY)
        self._update_state(result)
        return self._check_command_result(result, 1, {0x80})

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(STRIP_OFF_KEY)
        self._update_state(result)
        return self._check_command_result(result, 1, {0x00})

    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        result = await self._send_command(f"{BRIGHTNESS_KEY}{brightness:02X}")
        self._update_state(result)
        return self._check_command_result(result, 1, {0x80})

    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        # not supported on this device

    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 0 <= r <= 255, "r must be between 0 and 255"
        assert 0 <= g <= 255, "g must be between 0 and 255"
        assert 0 <= b <= 255, "b must be between 0 and 255"
        result = await self._send_command(
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
        self._override_state(
            {
                "isOn": result[1] == 0x80,
                "color_mode": result[10],
            }
        )
        _LOGGER.debug("%s: update state: %s = %s", self.name, result.hex(), self._state)
        self._fire_callbacks()
