"""Library to handle connection with Switchbot."""
from __future__ import annotations


def process_wocurtain(
    data: bytes | None, mfr_data: bytes | None, reverse: bool = True
) -> dict[str, bool | int]:
    """Process woCurtain/Curtain services data."""
    if mfr_data and len(mfr_data) >= 11:
        device_data = mfr_data[8:11]
    elif data:
        device_data = data[3:6]
    else:
        return {}

    _position = max(min(device_data[0] & 0b01111111, 100), 0)
    _in_motion = bool(device_data[0] & 0b10000000)
    _light_level = (device_data[1] >> 4) & 0b00001111
    _device_chain = device_data[1] & 0b00000111

    return {
        "calibration": bool(data[1] & 0b01000000) if data else None,
        "battery": data[2] & 0b01111111 if data else None,
        "inMotion": _in_motion,
        "position": (100 - _position) if reverse else _position,
        "lightLevel": _light_level,
        "deviceChain": _device_chain,
    }