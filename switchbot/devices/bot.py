"""Library to handle connection with Switchbot."""
from __future__ import annotations

from typing import Any

from .device import DEVICE_SET_EXTENDED_KEY, DEVICE_SET_MODE_KEY, SwitchbotDevice

# Bot keys
PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"
DOWN_KEY = "570103"
UP_KEY = "570104"


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Bot/WoHand constructor."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)

    async def update(self, interface: int | None = None) -> None:
        """Update mode, battery percent and state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(ON_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(OFF_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def hand_up(self) -> bool:
        """Raise device arm."""
        result = await self._send_command(UP_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def hand_down(self) -> bool:
        """Lower device arm."""
        result = await self._send_command(DOWN_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def press(self) -> bool:
        """Press command to device."""
        result = await self._send_command(PRESS_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def set_switch_mode(
        self, switch_mode: bool = False, strength: int = 100, inverse: bool = False
    ) -> bool:
        """Change bot mode."""
        mode_key = format(switch_mode, "b") + format(inverse, "b")
        strength_key = f"{strength:0{2}x}"  # to hex with padding to double digit
        result = await self._send_command(DEVICE_SET_MODE_KEY + strength_key + mode_key)
        return self._check_command_result(result, 0, {1})

    async def set_long_press(self, duration: int = 0) -> bool:
        """Set bot long press duration."""
        duration_key = f"{duration:0{2}x}"  # to hex with padding to double digit
        result = await self._send_command(DEVICE_SET_EXTENDED_KEY + "08" + duration_key)
        return self._check_command_result(result, 0, {1})

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
