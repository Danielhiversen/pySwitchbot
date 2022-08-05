"""Library to handle connection with Switchbot."""
from __future__ import annotations

from .adv_parser import SwitchbotSupportedType, parse_advertisement_data
from .const import SwitchbotModel
from .devices.bot import Switchbot
from .devices.curtain import SwitchbotCurtain
from .devices.device import SwitchbotDevice
from .devices.plug import SwitchbotPlugMini
from .discovery import GetSwitchbotDevices
from .models import SwitchBotAdvertisement

__all__ = [
    "parse_advertisement_data",
    "GetSwitchbotDevices",
    "SwitchBotAdvertisement",
    "SwitchbotDevice",
    "SwitchbotCurtain",
    "Switchbot",
    "SwitchbotPlugMini",
    "SwitchbotSupportedType",
    "SwitchbotModel",
]
