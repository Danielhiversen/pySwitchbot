"""Library to handle connection with Switchbot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bleak.backends.device import BLEDevice


@dataclass
class SwitchBotAdvertisement:
    """Switchbot advertisement."""

    address: str
    data: dict[str, Any]
    device: BLEDevice
    rssi: int
    active: bool = False
