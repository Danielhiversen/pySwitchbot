from __future__ import annotations

import logging
from typing import Any

from .base_light import SwitchbotBaseLight
from .device import REQ_HEADER, ColorMode

CEILING_LIGHT_COMMAND_HEADER = "5401"
CEILING_LIGHT_REQUEST = f"{REQ_HEADER}5501"

CEILING_LIGHT_COMMAND = f"{REQ_HEADER}{CEILING_LIGHT_COMMAND_HEADER}"
CEILING_LIGHT_ON_KEY = f"{CEILING_LIGHT_COMMAND}01FF01FFFF"
CEILING_LIGHT_OFF_KEY = f"{CEILING_LIGHT_COMMAND}02FF01FFFF"
CW_BRIGHTNESS_KEY = f"{CEILING_LIGHT_COMMAND}010001"
BRIGHTNESS_KEY = f"{CEILING_LIGHT_COMMAND}01FF01"


_LOGGER = logging.getLogger(__name__)


class SwitchbotCeilingLight(SwitchbotBaseLight):
    """Representation of a Switchbot bulb."""

    @property
    def color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.COLOR_TEMP}

    async def update(self) -> None:
        """Update state of device."""

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(CEILING_LIGHT_ON_KEY)
        ret = self._check_command_result(result, 0, {0x01})
        self._override_adv_data = {"isOn": True}
        self._fire_callbacks()
        return ret

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(CEILING_LIGHT_OFF_KEY)
        ret = self._check_command_result(result, 0, {0x01})
        self._override_adv_data = {"isOn": False}
        self._fire_callbacks()
        return ret

    async def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        result = await self._send_command(f"{BRIGHTNESS_KEY}{brightness:02X}0FA1")
        ret = self._check_command_result(result, 0, {0x01})
        self._override_adv_data = {"brightness": brightness, "isOn": True}
        self._fire_callbacks()
        return ret

    async def set_color_temp(self, brightness: int, color_temp: int) -> bool:
        """Set color temp."""
        assert 0 <= brightness <= 100, "Brightness must be between 0 and 100"
        assert 2700 <= color_temp <= 6500, "Color Temp must be between 0 and 100"
        result = await self._send_command(
            f"{CW_BRIGHTNESS_KEY}{brightness:02X}{color_temp:04X}"
        )
        ret = self._check_command_result(result, 0, {0x01})
        self._state["cw"] = color_temp
        self._override_adv_data = {"brightness": brightness, "isOn": True}
        self._fire_callbacks()
        return ret

    async def set_rgb(self, brightness: int, r: int, g: int, b: int) -> bool:
        """Set rgb."""
        # Not supported on this device
