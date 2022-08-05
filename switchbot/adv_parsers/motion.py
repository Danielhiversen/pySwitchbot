"""Motion sensor parser."""
from __future__ import annotations


def process_wopresence(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process WoPresence Sensor services data."""
    return {
        "tested": bool(data[1] & 0b10000000),
        "motion_detected": bool(data[1] & 0b01000000),
        "battery": data[2] & 0b01111111,
        "led": (data[5] & 0b00100000) >> 5,
        "iot": (data[5] & 0b00010000) >> 4,
        "sense_distance": (data[5] & 0b00001100) >> 2,
        "light_intensity": data[5] & 0b00000011,
        "is_light": bool(data[5] & 0b00000010),
    }
