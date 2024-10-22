"""Keypad parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def process_wokeypad(
    data: bytes | None, mfr_data: bytes | None, lastStatus: list[int] = [-1]
) -> dict[str, bool | int | None]:
    """Process woKeypad services data."""
    if data is None or mfr_data is None:
        lastStatus[0] = -1
        return {"battery": None, "attemptState": None}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    success = lastStatus[0] != -1 and (
        (mfr_data[6] > lastStatus[0] and mfr_data[6] - lastStatus[0] >= 2)
        or (mfr_data[6] < lastStatus[0] and mfr_data[6] - lastStatus[0] >= -254)
    )
    lastStatus[0] = mfr_data[6]

    return {"battery": data[2], "success": success}
