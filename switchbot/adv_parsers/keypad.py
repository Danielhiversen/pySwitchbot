"""Keypad parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

lastStatus = -1


def process_wokeypad(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | None]:
    """Process woKeypad services data."""
    if data is None or mfr_data is None:
        return {"battery": None, "attemptState": None}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    global lastStatus
    success = lastStatus != -1 and (
        (mfr_data[6] > lastStatus and mfr_data[6] - lastStatus >= 2)
        or (mfr_data[6] < lastStatus and mfr_data[6] - lastStatus >= -254)
    )
    lastStatus = mfr_data[6]

    return {"battery": data[2], "success": success}
