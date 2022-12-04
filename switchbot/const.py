"""Library to handle connection with Switchbot."""
from __future__ import annotations

from enum import Enum

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

from .enum import StrEnum


class SwitchbotModel(StrEnum):

    BOT = "WoHand"
    CURTAIN = "WoCurtain"
    HUMIDIFIER = "WoHumi"
    PLUG_MINI = "WoPlug"
    CONTACT_SENSOR = "WoContact"
    LIGHT_STRIP = "WoStrip"
    METER = "WoSensorTH"
    MOTION_SENSOR = "WoPresence"
    COLOR_BULB = "WoBulb"
    CEILING_LIGHT = "WoCeiling"
    LOCK = "WoLock"


class LockStatus(Enum):
    LOCKED = 0b0000000
    UNLOCKED = 0b0010000
    LOCKING = 0b0100000
    UNLOCKING = 0b0110000
    LOCKING_STOP = 0b1000000
    UNLOCKING_STOP = 0b1010000
    NOT_FULLY_LOCKED = 0b1100000  # Only EU lock type
