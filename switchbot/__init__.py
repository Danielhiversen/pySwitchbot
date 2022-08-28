"""Library to handle connection with Switchbot."""
from __future__ import annotations

from .adv_parser import SwitchbotSupportedType, parse_advertisement_data
from .const import SwitchbotModel
from .devices.base_light import SwitchbotBaseLight
from .devices.bot import Switchbot
from .devices.bulb import SwitchbotBulb
from .devices.curtain import SwitchbotCurtain
from .devices.device import ColorMode, SwitchbotDevice
from .devices.light_strip import SwitchbotLightStrip
from .devices.plug import SwitchbotPlugMini
from .discovery import GetSwitchbotDevices
from .models import SwitchBotAdvertisement

__all__ = [
    "parse_advertisement_data",
    "GetSwitchbotDevices",
    "SwitchBotAdvertisement",
    "ColorMode",
    "SwitchbotBaseLight",
    "SwitchbotBulb",
    "SwitchbotDevice",
    "SwitchbotCurtain",
    "SwitchbotLightStrip",
    "Switchbot",
    "SwitchbotPlugMini",
    "SwitchbotSupportedType",
    "SwitchbotModel",
]
