"""Library to handle connection with Switchbot."""
from __future__ import annotations

from bleak_retry_connector import close_stale_connections, get_device

from .adv_parser import SwitchbotSupportedType, parse_advertisement_data
from .const import SwitchbotModel
from .devices.base_light import SwitchbotBaseLight
from .devices.bot import Switchbot
from .devices.bulb import SwitchbotBulb
from .devices.ceiling_light import SwitchbotCeilingLight
from .devices.curtain import SwitchbotCurtain
from .devices.device import ColorMode, SwitchbotDevice
from .devices.humidifier import SwitchbotHumidifier
from .devices.light_strip import SwitchbotLightStrip
from .devices.plug import SwitchbotPlugMini
from .discovery import GetSwitchbotDevices
from .models import SwitchBotAdvertisement

__all__ = [
    "get_device",
    "close_stale_connections",
    "parse_advertisement_data",
    "GetSwitchbotDevices",
    "SwitchBotAdvertisement",
    "ColorMode",
    "SwitchbotBaseLight",
    "SwitchbotBulb",
    "SwitchbotCeilingLight",
    "SwitchbotDevice",
    "SwitchbotCurtain",
    "SwitchbotLightStrip",
    "SwitchbotHumidifier",
    "Switchbot",
    "SwitchbotPlugMini",
    "SwitchbotSupportedType",
    "SwitchbotModel",
]
