"""Lock parser."""

from __future__ import annotations

import logging

from ..const import LockStatus

_LOGGER = logging.getLogger(__name__)


def process_wolock(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woLock services data."""
    if mfr_data is None:
        return {}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    return {
        "battery": data[2] & 0b01111111 if data else None,
        "calibration": bool(mfr_data[7] & 0b10000000),
        "status": LockStatus((mfr_data[7] & 0b01110000) >> 4),
        "update_from_secondary_lock": bool(mfr_data[7] & 0b00001000),
        "door_open": bool(mfr_data[7] & 0b00000100),
        "double_lock_mode": bool(mfr_data[8] & 0b10000000),
        "unclosed_alarm": bool(mfr_data[8] & 0b00100000),
        "unlocked_alarm": bool(mfr_data[8] & 0b00010000),
        "auto_lock_paused": bool(mfr_data[8] & 0b00000010),
        "night_latch": bool(mfr_data[9] & 0b00000001) if len(mfr_data) > 9 else False,
    }


def process_wolock_pro(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    res = {
        "battery": data[2] & 0b01111111 if data else None,
        "calibration": bool(mfr_data[7] & 0b10000000),
        "status": LockStatus((mfr_data[7] & 0b00111000) >> 3),
        "door_open": bool(mfr_data[8] & 0b01100000),
        # Double lock mode is not supported on Lock Pro
        "update_from_secondary_lock": False,
        "double_lock_mode": False,
        "unclosed_alarm": bool(mfr_data[11] & 0b10000000),
        "unlocked_alarm": bool(mfr_data[11] & 0b01000000),
        "auto_lock_paused": bool(mfr_data[8] & 0b100000),
        # Looks like night latch bit is not anymore in ADV
        "night_latch": False,
    }
    _LOGGER.debug(res)
    return res
