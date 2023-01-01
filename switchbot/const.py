"""Library to handle connection with Switchbot."""
from __future__ import annotations

from enum import Enum

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

from .enum import StrEnum


class SwitchbotAuthenticationError(RuntimeError):
    """Raised when authentication fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class SwitchbotAccountConnectionError(RuntimeError):
    """Raised when connection to Switchbot account fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


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
    LOCKED = 0
    UNLOCKED = 1
    LOCKING = 2
    UNLOCKING = 3
    LOCKING_STOP = 4  # LOCKING_BLOCKED
    UNLOCKING_STOP = 5  # UNLOCKING_BLOCKED
    NOT_FULLY_LOCKED = 6  # LATCH_LOCKED - Only EU lock type
