"""Motion sensor parser."""

from __future__ import annotations


def process_wopresence(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoPresence Sensor services data."""
    if data is None and mfr_data is None:
        return {}
    tested = None
    battery = None
    led = None
    iot = None
    sense_distance = None
    light_intensity = None
    is_light = None

    if data:
        tested = bool(data[1] & 0b10000000)
        motion_detected = bool(data[1] & 0b01000000)
        battery = data[2] & 0b01111111
        led = (data[5] & 0b00100000) >> 5
        iot = (data[5] & 0b00010000) >> 4
        sense_distance = (data[5] & 0b00001100) >> 2
        light_intensity = data[5] & 0b00000011
        is_light = bool(data[5] & 0b00000010)
    if mfr_data and len(mfr_data) >= 8:
        motion_detected = bool(mfr_data[7] & 0b01000000)
        is_light = bool(mfr_data[7] & 0b00100000)

    return {
        "tested": tested,
        "motion_detected": motion_detected,
        "battery": battery,
        "led": led,
        "iot": iot,
        "sense_distance": sense_distance,
        "light_intensity": light_intensity,
        "is_light": is_light,
    }
