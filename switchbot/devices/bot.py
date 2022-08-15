"""Library to handle connection with Switchbot."""
from __future__ import annotations

import logging
from typing import Any

from .device import DEVICE_SET_EXTENDED_KEY, DEVICE_SET_MODE_KEY, SwitchbotDevice

# Bot keys
PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"
DOWN_KEY = "570103"
UP_KEY = "570104"


_LOGGER = logging.getLogger(__name__)


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Bot/WoHand constructor."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)
        self._settings: dict[str, Any] = {}

    async def update(self, interface: int | None = None) -> None:
        """Update mode, battery percent and state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._sendcommand(ON_KEY, self._retry_count)

        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug(
                "%s: Bot is in press mode and doesn't have on state", self.name
            )
            return True

        return False

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._sendcommand(OFF_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug(
                "%s: Bot is in press mode and doesn't have off state", self.name
            )
            return True

        return False

    async def hand_up(self) -> bool:
        """Raise device arm."""
        result = await self._sendcommand(UP_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("%s: Bot is in press mode", self.name)
            return True

        return False

    async def hand_down(self) -> bool:
        """Lower device arm."""
        result = await self._sendcommand(DOWN_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("%s: Bot is in press mode", self.name)
            return True

        return False

    async def press(self) -> bool:
        """Press command to device."""
        result = await self._sendcommand(PRESS_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("%s: Bot is in switch mode", self.name)
            return True

        return False

    async def set_switch_mode(
        self, switch_mode: bool = False, strength: int = 100, inverse: bool = False
    ) -> bool:
        """Change bot mode."""
        mode_key = format(switch_mode, "b") + format(inverse, "b")
        strength_key = f"{strength:0{2}x}"  # to hex with padding to double digit

        result = await self._sendcommand(
            DEVICE_SET_MODE_KEY + strength_key + mode_key, self._retry_count
        )

        if result[0] == 1:
            return True

        return False

    async def set_long_press(self, duration: int = 0) -> bool:
        """Set bot long press duration."""
        duration_key = f"{duration:0{2}x}"  # to hex with padding to double digit

        result = await self._sendcommand(
            DEVICE_SET_EXTENDED_KEY + "08" + duration_key, self._retry_count
        )

        if result[0] == 1:
            return True

        return False

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "strength": _data[3],
            "timers": _data[8],
            "switchMode": bool(_data[9] & 16),
            "inverseDirection": bool(_data[9] & 1),
            "holdSeconds": _data[10],
        }

    def switch_mode(self) -> Any:
        """Return true or false from cache."""
        # To get actual position call update() first.
        return self._get_adv_value("switchMode")

    def is_on(self) -> Any:
        """Return switch state from cache."""
        # To get actual position call update() first.
        value = self._get_adv_value("isOn")
        if value is None:
            return None

        if self._inverse:
            return not value
        return value
