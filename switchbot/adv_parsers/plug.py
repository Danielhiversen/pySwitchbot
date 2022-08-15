"""Library to handle connection with Switchbot."""
from __future__ import annotations


def process_woplugmini(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process plug mini."""
    assert mfr_data is not None
    return {
        "switchMode": True,
        "isOn": mfr_data[7] == 0x80,
        "wifi_rssi": -mfr_data[9],
    }
