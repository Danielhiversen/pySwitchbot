"""Keypad parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def process_wokeypad(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | None] | {}:
    """Process woKeypad services data."""
    if data is None and mfr_data is None:
        return {}

    if data is None:
        return {"battery": None, "attemptState": None}

    _LOGGER.debug("mfr_data: %s", mfr_data.hex())
    if data:
        _LOGGER.debug("data: %s", data.hex())

    return {"battery": data[2], "attemptState": mfr_data[6]}
