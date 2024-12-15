"""Library to handle connection with Switchbot."""

from __future__ import annotations

import time

from .device import REQ_HEADER, SwitchbotDevice

HUMIDIFIER_COMMAND_HEADER = "4381"
HUMIDIFIER_REQUEST = f"{REQ_HEADER}4481"
HUMIDIFIER_COMMAND = f"{REQ_HEADER}{HUMIDIFIER_COMMAND_HEADER}"
HUMIDIFIER_OFF_KEY = f"{HUMIDIFIER_COMMAND}010080FFFFFFFF"
HUMIDIFIER_ON_KEY = f"{HUMIDIFIER_COMMAND}010180FFFFFFFF"
##
# OFF    570F 4381 0100 80FF FFFF FF
# ON     570F 4381 0101 80FF FFFF FF
# AUTO   570F 4381 0101 80FF FFFF FF
# 1.     570F 4381 0101 22FF FFFF FF
# 2.     570F 4381 0101 43FF FFFF FF
# 3    . 570F 4381 0101 64FF FFFF FF

MANUAL_BUTTON_PRESSES_TO_LEVEL = {
    101: 33,
    102: 66,
    103: 100,
}


class SwitchbotHumidifier(SwitchbotDevice):
    """Representation of a Switchbot humidifier."""

    async def update(self, interface: int | None = None) -> None:
        """Update state of device."""
        # No battery here
        self._last_full_update = time.monotonic()

    def _generate_command(
        self, on: bool | None = None, level: int | None = None
    ) -> str:
        """Generate command."""
        if level is None:
            level = self.get_target_humidity() or 128
        if on is None:
            on = self.is_on()
        on_hex = "01" if on else "00"
        return f"{HUMIDIFIER_COMMAND}01{on_hex}{level:02X}FFFFFFFF"

    async def _async_set_state(self, state: bool) -> bool:
        level = self.get_target_humidity() or 128
        result = await self._send_command(self._generate_command(on=state, level=level))
        ret = self._check_command_result(result, 0, {0x01})
        self._override_state({"isOn": state, "level": level})
        self._fire_callbacks()
        return ret

    async def turn_on(self) -> bool:
        """Turn device on."""
        await self._async_set_state(True)

    async def turn_off(self) -> bool:
        """Turn device off."""
        await self._async_set_state(False)

    async def set_level(self, level: int) -> bool:
        """Set level."""
        assert 1 <= level <= 100, "Level must be between 1 and 100"
        await self._set_level(level)

    async def _set_level(self, level: int) -> bool:
        """Set level."""
        result = await self._send_command(self._generate_command(level=level))
        ret = self._check_command_result(result, 0, {0x01})
        self._override_state({"level": level})
        self._fire_callbacks()
        return ret

    async def async_set_auto(self) -> bool:
        """Set auto mode."""
        await self._set_level(128)

    async def async_set_manual(self) -> bool:
        """Set manual mode."""
        await self._set_level(50)

    def is_auto(self) -> bool:
        """Return auto state from cache."""
        return self.get_level() in (228, 128)

    def get_level(self) -> int | None:
        """Return level state from cache."""
        return self._get_adv_value("level")

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn")

    def get_target_humidity(self) -> int | None:
        """Return target humidity from cache."""
        level = self.get_level()
        if self.is_auto():
            return None
        return MANUAL_BUTTON_PRESSES_TO_LEVEL.get(level, level)

    def poll_needed(self, last_poll_time: float | None) -> bool:
        """Return if device needs polling."""
        return False
