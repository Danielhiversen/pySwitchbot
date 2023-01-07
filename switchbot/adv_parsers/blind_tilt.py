"""Library to handle connection with Switchbot."""
from __future__ import annotations


def process_woblindtilt(
    data: bytes | None, mfr_data: bytes | None, reverse: bool = True
) -> dict[str, bool | int]:
    """Process woBlindTilt services data."""

    if mfr_data is None:
        return {}

    device_data = mfr_data[6:]

    _tilt = max(min(device_data[2] & 0b00111111, 100), 0)
    _in_motion = bool(device_data[2] & 0b10000000)
    _light_level = (device_data[1] >> 4) & 0b00001111

    return {
        "calibration": bool(data[1] & 0b01000000) if data else None,
        "battery": data[2] & 0b01111111 if data else None,
        "inMotion": _in_motion,
        "tilt": (100 - _tilt) if reverse else _tilt,
        "lightLevel": _light_level,
    }
