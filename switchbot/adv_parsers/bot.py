"""Library to handle connection with Switchbot."""
from __future__ import annotations


def process_wohand(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woHand/Bot services data."""
    _switch_mode = bool(data[1] & 0b10000000)

    return {
        "switchMode": _switch_mode,
        "isOn": not bool(data[1] & 0b01000000) if _switch_mode else False,
        "battery": data[2] & 0b01111111,
    }
