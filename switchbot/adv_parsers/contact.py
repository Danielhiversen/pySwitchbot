"""Contact sensor parser."""
from __future__ import annotations


def process_wocontact(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woContact Sensor services data."""
    return {
        "tested": bool(data[1] & 0b10000000),
        "motion_detected": bool(data[1] & 0b01000000),
        "battery": data[2] & 0b01111111,
        "contact_open": data[3] & 0b00000010 == 0b00000010,
        "contact_timeout": data[3] & 0b00000110 == 0b00000110,
        "is_light": bool(data[3] & 0b00000001),
        "button_count": (data[7] & 0b11110000) >> 4,
    }
