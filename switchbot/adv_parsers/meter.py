"""Meter parser."""
from __future__ import annotations

from typing import Any


def process_wosensorth(data: bytes, mfr_data: bytes | None) -> dict[str, Any]:
    """Process woSensorTH/Temp sensor services data."""

    _temp_sign = 1 if data[4] & 0b10000000 else -1
    _temp_c = _temp_sign * ((data[4] & 0b01111111) + ((data[3] & 0b00001111) / 10))
    _temp_f = (_temp_c * 9 / 5) + 32
    _temp_f = (_temp_f * 10) / 10

    _wosensorth_data = {
        "temp": {"c": _temp_c, "f": _temp_f},
        "fahrenheit": bool(data[5] & 0b10000000),
        "humidity": data[5] & 0b01111111,
        "battery": data[2] & 0b01111111,
    }

    return _wosensorth_data
