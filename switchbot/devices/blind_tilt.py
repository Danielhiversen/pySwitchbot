"""Library to handle connection with Switchbot."""
from __future__ import annotations

import logging
from typing import Any

from .curtain import SwitchbotCurtain, CURTAIN_EXT_SUM_KEY

_LOGGER = logging.getLogger(__name__)


class SwitchbotBlindTilt(SwitchbotCurtain):
    """Representation of a Switchbot Blind Tilt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Blind Tilt/woBlindTilt constructor."""

        super().__init__(*args, **kwargs)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        _position = max(min(_data[6], 100), 0)
        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "light": bool(_data[4] & 0b00100000),
            "fault": bool(_data[4] & 0b00001000),
            "solarPanel": bool(_data[5] & 0b00001000),
            "calibration": bool(_data[5] & 0b00000100),
            "calibrated": bool(_data[5] & 0b00000100),
            "inMotion": bool(_data[5] & 0b00000011),
            "motionDirection": {
                "up": bool(_data[5] & (0b00000010 if self._reverse else 0b00000001)),
                "down": bool(_data[5] & (0b00000001 if self._reverse else 0b00000010)),
            },
            "position": (100 - _position) if self._reverse else _position,
            "timers": _data[7],
        }

    async def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get basic info for all devices in chain."""
        _data = await self._send_command(key=CURTAIN_EXT_SUM_KEY)

        if not _data:
            _LOGGER.error("%s: Unsuccessful, no result from device", self.name)
            return None

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("%s: Unsuccessful, please try again", self.name)
            return None

        self.ext_info_sum["device0"] = {
            "light": bool(_data[1] & 0b00100000),
        }

        return self.ext_info_sum
