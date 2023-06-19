"""Library to handle connection with Switchbot."""
from __future__ import annotations

import logging
from typing import Any

from switchbot.devices.device import (
    REQ_HEADER,
    SwitchbotSequenceDevice,
    update_after_operation,
)

from .curtain import CURTAIN_EXT_SUM_KEY, SwitchbotCurtain

_LOGGER = logging.getLogger(__name__)


BLIND_COMMAND = "4501"
OPEN_KEYS = [
    f"{REQ_HEADER}{BLIND_COMMAND}010132",
    f"{REQ_HEADER}{BLIND_COMMAND}05ff32",
]
CLOSE_DOWN_KEYS = [
    f"{REQ_HEADER}{BLIND_COMMAND}010100",
    f"{REQ_HEADER}{BLIND_COMMAND}05ff00",
]
CLOSE_UP_KEYS = [
    f"{REQ_HEADER}{BLIND_COMMAND}010164",
    f"{REQ_HEADER}{BLIND_COMMAND}05ff64",
]


class SwitchbotBlindTilt(SwitchbotCurtain, SwitchbotSequenceDevice):
    """Representation of a Switchbot Blind Tilt."""

    # The position of the blind is saved returned with 0 = closed down, 50 = open and 100 = closed up.
    # This is independent of the calibration of the blind.
    # The parameter 'reverse_mode' reverse these values,
    # if 'reverse_mode' = True, position = 0 equals closed up
    # and position = 100 equals closed down. The parameter is default set to False so that
    # the definition of position is the same as in Home Assistant.
    # This is opposite to the base class so needs to be overwritten.

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Blind Tilt/woBlindTilt constructor."""
        super().__init__(*args, **kwargs)

        self._reverse: bool = kwargs.pop("reverse_mode", False)

    @update_after_operation
    async def open(self) -> bool:
        """Send open command."""
        return await self._send_multiple_commands(OPEN_KEYS)

    @update_after_operation
    async def close_up(self) -> bool:
        """Send close up command."""
        return await self._send_multiple_commands(CLOSE_UP_KEYS)

    @update_after_operation
    async def close_down(self) -> bool:
        """Send close down command."""
        return await self._send_multiple_commands(CLOSE_DOWN_KEYS)

    # The aim of this is to close to the nearest endpoint.
    # If we're open upwards we close up, if we're open downwards we close down.
    # If we're in the middle we default to close down as that seems to be the app's preference.
    @update_after_operation
    async def close(self) -> bool:
        """Send close command."""
        if self.get_position() > 50:
            return await self.close_up()
        else:
            return await self.close_down()

    def get_position(self) -> Any:
        """Return cached tilt (0-100) of Blind Tilt."""
        # To get actual tilt call update() first.
        return self._get_adv_value("tilt")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        _tilt = max(min(_data[6], 100), 0)
        _moving = bool(_data[5] & 0b00000011)
        if _moving:
            _opening = bool(_data[5] & 0b00000010)
            _closing = not _opening and bool(_data[5] & 0b00000001)
            if _opening:
                _flag = bool(_data[5] & 0b00000001)
                _up = _flag if self._reverse else not _flag
            else:
                _up = _tilt < 50 if self._reverse else _tilt > 50

        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "light": bool(_data[4] & 0b00100000),
            "fault": bool(_data[4] & 0b00001000),
            "solarPanel": bool(_data[5] & 0b00001000),
            "calibration": bool(_data[5] & 0b00000100),
            "calibrated": bool(_data[5] & 0b00000100),
            "inMotion": _moving,
            "motionDirection": {
                "opening": _moving and _opening,
                "closing": _moving and _closing,
                "up": _moving and _up,
                "down": _moving and not _up,
            },
            "tilt": (100 - _tilt) if self._reverse else _tilt,
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
