"""Light strip adv parser."""
from __future__ import annotations
import binascii


def process_worelay_switch_1pm(
        data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoStrip services data."""
    if mfr_data is None:
        return {}
    print("mfr_data: %s, isOn: %d, power: %d" % (binascii.hexlify(mfr_data).decode('utf-8'), bool(mfr_data[7] & 0b10000000), ((mfr_data[10] << 8) + mfr_data[11]) / 10))
    return {
        "switchMode": True, # for compatibility, useless
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "power": ((mfr_data[10] << 8) + mfr_data[11]) / 10,
        "voltage": 0,
        "current": 0,
    }


def process_worelay_switch_1plus(
        data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process WoStrip services data."""
    if mfr_data is None:
        return {}
    print("mfr_data: %s, isOn: %d" % (binascii.hexlify(mfr_data).decode('utf-8'), bool(mfr_data[7] & 0b10000000)))
    return {
        "switchMode": True, # for compatibility, useless
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000)
    }
