"""Library to handle connection with Switchbot."""
from __future__ import annotations

from typing import Any

from .device import SwitchbotDevice

# Plug Mini keys
PLUG_ON_KEY = "570f50010180"
PLUG_OFF_KEY = "570f50010100"


class SwitchbotPlugMini(SwitchbotDevice):
    """Representation of a Switchbot plug mini."""

    async def update(self, interface: int | None = None) -> None:
        """Update state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(PLUG_ON_KEY)
        return self._check_command_result(result, 1, {0x80})

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(PLUG_OFF_KEY)
        return self._check_command_result(result, 1, {0x00})

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn")
