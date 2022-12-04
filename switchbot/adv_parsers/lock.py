"""Lock parser."""
from __future__ import annotations

import logging

from ..const import LockStatus

_LOGGER = logging.getLogger(__name__)


def process_wolock(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woLock services data."""
    if mfr_data is None:
        return {}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    _LOGGER.debug("data: %s", data.hex())

    return {
        "battery": data[2] & 0b01111111,
        "calibration": bool(mfr_data[7] & 0b10000000),
        "status": LockStatus(mfr_data[7] & 0b01110000),
        "update_from_secondary_lock": bool(mfr_data[7] & 0b00001000),
        "door_open": bool(mfr_data[7] & 0b00000100),
        "double_lock_mode": bool(mfr_data[8] & 0b10000000),
        "unclosed_alarm": bool(mfr_data[8] & 0b00100000),
        "unlocked_alarm": bool(mfr_data[8] & 0b00010000),
        "auto_lock_paused": bool(mfr_data[8] & 0b00000010),
    }
