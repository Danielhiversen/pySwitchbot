"""Relay Switch adv parser."""

from __future__ import annotations


def process_worelay_switch_1pm(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoStrip services data."""
    if mfr_data is None:
        return {}
    return {
        "switchMode": True,  # for compatibility, useless
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "power": ((mfr_data[10] << 8) + mfr_data[11]) / 10,
        "voltage": 0,
        "current": 0,
    }


def process_worelay_switch_1(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoStrip services data."""
    if mfr_data is None:
        return {}
    return {
        "switchMode": True,  # for compatibility, useless
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
    }
