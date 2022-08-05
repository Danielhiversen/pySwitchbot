"""Library to handle connection with Switchbot."""


def process_woplugmini(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process plug mini."""
    return {
        "switchMode": True,
        "isOn": mfr_data[7] == 0x80,
        "wifi_rssi": -mfr_data[9],
    }
