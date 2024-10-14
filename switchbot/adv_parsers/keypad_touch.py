"""Keypad Touch parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def process_wokeypad_touch(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process woKeypadTouch services data."""
    if mfr_data is None:
        return {}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    return {"battery": data[2], "attemptState": mfr_data[6]}
