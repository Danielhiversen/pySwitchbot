"""Library to handle connection with Switchbot."""
from __future__ import annotations

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


class SwitchbotHumidifier(SwitchbotDevice):
    """Representation of a Switchbot humidifier."""

    async def update(self, interface: int | None = None) -> None:
        """Update state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(HUMIDIFIER_ON_KEY)
        ret = self._check_command_result(result, 0, {0x01})
        self._override_adv_data = {"isOn": True}
        self._fire_callbacks()
        return ret

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(HUMIDIFIER_OFF_KEY)
        ret = self._check_command_result(result, 0, {0x01})
        self._override_adv_data = {"isOn": False}
        self._fire_callbacks()
        return ret

    async def set_level(self, level: int) -> bool:
        """Set level."""
        assert 1 <= level <= 100, "Level must be between 1 and 100"
        result = await self._send_command(
            f"{HUMIDIFIER_COMMAND}0101{level:02X}FFFFFFFF"
        )
        ret = self._check_command_result(result, 0, {0x01})
        self._override_adv_data = {"isOn": False, "level": level}
        self._fire_callbacks()
        return ret

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn")
