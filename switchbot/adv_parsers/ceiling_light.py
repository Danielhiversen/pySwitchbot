"""Ceiling Light adv parser."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

# Off d94b2d012b3c4864106124
# on  d94b2d012b3c4a641061a4
# Off d94b2d012b3c4b64106124
# on  d94b2d012b3c4d641061a4
#     00112233445566778899AA


def process_woceiling(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process WoCeiling services data."""
    if mfr_data is None:
        return {}
    return {
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[10] & 0b10000000),
        "brightness": mfr_data[7] & 0b01111111,
        "cw": int(mfr_data[8:10].hex(), 16),
        "color_mode": 1,
    }
