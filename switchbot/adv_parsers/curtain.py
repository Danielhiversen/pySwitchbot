"""Library to handle connection with Switchbot."""
from __future__ import annotations


def process_wocurtain(
    data: bytes, mfr_data: bytes | None, reverse: bool = True
) -> dict[str, bool | int]:
    """Process woCurtain/Curtain services data."""

    _position = max(min(data[3] & 0b01111111, 100), 0)

    return {
        "calibration": bool(data[1] & 0b01000000),
        "paired": not bool(data[1] & 0b00010000),
        "battery": data[2] & 0b01111111,
        "inMotion": bool(data[3] & 0b10000000),
        "position": (100 - _position) if reverse else _position,
        "lightLevel": (data[4] >> 4) & 0b00001111,
        "deviceChain": data[4] & 0b00000111,
    }

    # Paired Curtain
    # AdvertisementData(local_name='WoCurtain', manufacturer_data={89: b'\xd1K3\x1f\n\xfd'}, service_data={'00000d00-0000-1000-8000-00805f9b34fb': b'c@X\x00!\x04'}, service_uuids=['cba20d00-224d-11e6-9fb8-0002a5d5c51b']) connectable: True match: {'switchbot'} rssi: -40

    # Unpaired Curtain
    # AdvertisementData(local_name='WoCurtain', manufacturer_data={89: b'\xd1K3\x1f\n\xfd'}, service_data={'00000d00-0000-1000-8000-00805f9b34fb': b'c\xd0X\x00!\x04'}, service_uuids=['cba20d00-224d-11e6-9fb8-0002a5d5c51b']) connectable: True match: {'switchbot'} rssi: -40
