"""Meter parser."""
from __future__ import annotations

from typing import Any


def process_wosensorth(data: bytes | None, mfr_data: bytes | None) -> dict[str, Any]:
    """Process woSensorTH/Temp sensor services data."""
    if mfr_data:
        temp_data = mfr_data[8:11]
        battery = None

    if data:
        temp_data = data[3:6]
        battery = data[2] & 0b01111111

    if not temp_data:
        return {}

    _temp_sign = 1 if temp_data[1] & 0b10000000 else -1
    _temp_c = _temp_sign * (
        (temp_data[1] & 0b01111111) + ((temp_data[0] & 0b00001111) / 10)
    )
    _temp_f = (_temp_c * 9 / 5) + 32
    _temp_f = (_temp_f * 10) / 10

    _wosensorth_data = {
        # Data should be flat, but we keep the original structure for now
        "temp": {"c": _temp_c, "f": _temp_f},
        "temperature": _temp_c,
        "fahrenheit": bool(temp_data[2] & 0b10000000),
        "humidity": temp_data[2] & 0b01111111,
        "battery": battery,
    }

    return _wosensorth_data
