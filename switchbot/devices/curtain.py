"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
from typing import Any

from ..models import SwitchBotAdvertisement
from .base_cover import COVER_COMMAND, COVER_EXT_SUM_KEY, SwitchbotBaseCover
from .device import REQ_HEADER, update_after_operation

# For second element of open and close arrs we should add two bytes i.e. ff00
# First byte [ff] stands for speed (00 or ff - normal, 01 - slow) *
# * Only for curtains 3. For other models use ff
# Second byte [00] is a command (00 - open, 64 - close)
OPEN_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}010100",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed + "00"
]
CLOSE_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}010164",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed + "64"
]
POSITION_KEYS = [
    f"{REQ_HEADER}{COVER_COMMAND}0101",
    f"{REQ_HEADER}{COVER_COMMAND}05",  # +speed
]  # +actual_position
STOP_KEYS = [f"{REQ_HEADER}{COVER_COMMAND}0001", f"{REQ_HEADER}{COVER_COMMAND}00ff"]

CURTAIN_EXT_CHAIN_INFO_KEY = f"{REQ_HEADER}468101"


_LOGGER = logging.getLogger(__name__)


class SwitchbotCurtain(SwitchbotBaseCover):
    """Representation of a Switchbot Curtain."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Curtain/WoCurtain constructor."""

        # The position of the curtain is saved returned with 0 = open and 100 = closed.
        # This is independent of the calibration of the curtain bot (Open left to right/
        # Open right to left/Open from the middle).
        # The parameter 'reverse_mode' reverse these values,
        # if 'reverse_mode' = True, position = 0 equals close
        # and position = 100 equals open. The parameter is default set to True so that
        # the definition of position is the same as in Home Assistant.

        self._reverse: bool = kwargs.pop("reverse_mode", True)
        super().__init__(self._reverse, *args, **kwargs)
        self._settings: dict[str, Any] = {}
        self.ext_info_sum: dict[str, Any] = {}
        self.ext_info_adv: dict[str, Any] = {}

    def _set_parsed_data(
        self, advertisement: SwitchBotAdvertisement, data: dict[str, Any]
    ) -> None:
        """Set data."""
        in_motion = data["inMotion"]
        previous_position = self._get_adv_value("position")
        new_position = data["position"]
        self._update_motion_direction(in_motion, previous_position, new_position)
        super()._set_parsed_data(advertisement, data)

    @update_after_operation
    async def open(self, speed: int = 255) -> bool:
        """Send open command. Speed 255 - normal, 1 - slow"""
        self._is_opening = True
        self._is_closing = False
        return await self._send_multiple_commands(
            [OPEN_KEYS[0], f"{OPEN_KEYS[1]}{speed:02X}00"]
        )

    @update_after_operation
    async def close(self, speed: int = 255) -> bool:
        """Send close command. Speed 255 - normal, 1 - slow"""
        self._is_closing = True
        self._is_opening = False
        return await self._send_multiple_commands(
            [CLOSE_KEYS[0], f"{CLOSE_KEYS[1]}{speed:02X}64"]
        )

    @update_after_operation
    async def stop(self) -> bool:
        """Send stop command to device."""
        self._is_opening = self._is_closing = False
        return await super().stop()

    @update_after_operation
    async def set_position(self, position: int, speed: int = 255) -> bool:
        """Send position command (0-100) to device. Speed 255 - normal, 1 - slow"""
        direction_adjusted_position = (100 - position) if self._reverse else position
        self._update_motion_direction(
            True, self._get_adv_value("position"), direction_adjusted_position
        )
        return await super().set_position(position, speed)

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        return self._get_adv_value("position")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        _position = max(min(_data[6], 100), 0)
        _direction_adjusted_position = (100 - _position) if self._reverse else _position
        _previous_position = self._get_adv_value("position")
        _in_motion = bool(_data[5] & 0b01000011)
        self._update_motion_direction(
            _in_motion, _previous_position, _direction_adjusted_position
        )

        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "chainLength": _data[3],
            "openDirection": (
                "right_to_left" if _data[4] & 0b10000000 == 128 else "left_to_right"
            ),
            "touchToOpen": bool(_data[4] & 0b01000000),
            "light": bool(_data[4] & 0b00100000),
            "fault": bool(_data[4] & 0b00001000),
            "solarPanel": bool(_data[5] & 0b00001000),
            "calibration": bool(_data[5] & 0b00000100),
            "calibrated": bool(_data[5] & 0b00000100),
            "inMotion": _in_motion,
            "position": _direction_adjusted_position,
            "timers": _data[7],
        }

    def _update_motion_direction(
        self, in_motion: bool, previous_position: int | None, new_position: int
    ) -> None:
        """Update opening/closing status based on movement."""
        if previous_position is None:
            return
        if in_motion is False:
            self._is_closing = self._is_opening = False
            return

        if new_position != previous_position:
            self._is_opening = new_position > previous_position
            self._is_closing = new_position < previous_position

    async def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get extended info for all devices in chain."""
        _data = await self._send_command(key=COVER_EXT_SUM_KEY)

        if not _data:
            _LOGGER.error("%s: Unsuccessful, no result from device", self.name)
            return None

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("%s: Unsuccessful, please try again", self.name)
            return None

        self.ext_info_sum["device0"] = {
            "openDirectionDefault": not bool(_data[1] & 0b10000000),
            "touchToOpen": bool(_data[1] & 0b01000000),
            "light": bool(_data[1] & 0b00100000),
            "openDirection": (
                "left_to_right" if _data[1] & 0b00010000 else "right_to_left"
            ),
        }

        # if grouped curtain device present.
        if _data[2] != 0:
            self.ext_info_sum["device1"] = {
                "openDirectionDefault": not bool(_data[2] & 0b10000000),
                "touchToOpen": bool(_data[2] & 0b01000000),
                "light": bool(_data[2] & 0b00100000),
                "openDirection": (
                    "left_to_right" if _data[2] & 0b00010000 else "right_to_left"
                ),
            }

        return self.ext_info_sum
