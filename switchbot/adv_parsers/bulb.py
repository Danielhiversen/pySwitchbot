"""Bulb parser."""
from __future__ import annotations


def process_color_bulb(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process WoBulb services data."""
    if mfr_data is None:
        return {}
    return {
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "brightness": mfr_data[7] & 0b01111111,
        "delay": bool(mfr_data[8] & 0b10000000),
        "preset": bool(mfr_data[8] & 0b00001000),
        "color_mode": mfr_data[8] & 0b00000111,
        "speed": mfr_data[9] & 0b01111111,
        "loop_index": mfr_data[10] & 0b11111110,
    }
