"""Library to handle connection with Switchbot."""
from __future__ import annotations


def process_wocurtain(
    data: bytes, mfr_data: bytes | None, reverse: bool = True
) -> dict[str, bool | int]:
    """Process woCurtain/Curtain services data."""

    _position = max(min(data[3] & 0b01111111, 100), 0)

    return {
        "calibration": bool(data[1] & 0b01000000),
        "battery": data[2] & 0b01111111,
        "inMotion": bool(data[3] & 0b10000000),
        "position": (100 - _position) if reverse else _position,
        "lightLevel": (data[4] >> 4) & 0b00001111,
        "deviceChain": data[4] & 0b00000111,
    }
