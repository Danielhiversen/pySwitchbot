"""Contact sensor parser."""
from __future__ import annotations


def process_wocontact(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woContact Sensor services data."""
    battery = data[2] & 0b01111111
    tested = bool(data[1] & 0b10000000)
    contact_timeout = data[3] & 0b00000100 == 0b00000100

    if mfr_data and len(mfr_data) >= 13:
        motion_detected = bool(mfr_data[7] & 0b10000000)
        contact_open = bool(mfr_data[7] & 0b00010000)
        button_count = mfr_data[12] & 0b00001111
        is_light = bool(mfr_data[7] & 0b01000000)
    else:
        motion_detected = bool(data[1] & 0b01000000)
        contact_open = data[3] & 0b00000010 == 0b00000010
        button_count = data[8] & 0b00001111
        is_light = bool(data[3] & 0b00000001)

    return {
        "tested": tested,
        "motion_detected": motion_detected,
        "battery": battery,
        "contact_open": contact_open or contact_timeout,  # timeout still means its open
        "contact_timeout": contact_timeout,
        "is_light": is_light,
        "button_count": button_count,
    }
