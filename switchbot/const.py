"""Library to handle connection with Switchbot."""
from __future__ import annotations

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

from .enum import StrEnum


class SwitchbotModel(StrEnum):

    BOT = "WoHand"
    CURTAIN = "WoCurtain"
    PLUG_MINI = "WoPlug"
    CONTACT_SENSOR = "WoContact"
    METER = "WoSensorTH"
    MOTION_SENSOR = "WoPresence"
    COLOR_BULB = "WoBulb"
