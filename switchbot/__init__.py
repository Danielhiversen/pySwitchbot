"""Library to handle connection with Switchbot."""

from __future__ import annotations

from bleak_retry_connector import (
    close_stale_connections,
    close_stale_connections_by_address,
    get_device,
)

from .adv_parser import SwitchbotSupportedType, parse_advertisement_data
from .const import (
    LockStatus,
    SwitchbotAccountConnectionError,
    SwitchbotApiError,
    SwitchbotAuthenticationError,
    SwitchbotModel,
)
from .devices.device import SwitchbotEncryptedDevice
from .devices.base_light import SwitchbotBaseLight
from .devices.blind_tilt import SwitchbotBlindTilt
from .devices.bot import Switchbot
from .devices.bulb import SwitchbotBulb
from .devices.ceiling_light import SwitchbotCeilingLight
from .devices.curtain import SwitchbotCurtain
from .devices.device import ColorMode, SwitchbotDevice
from .devices.humidifier import SwitchbotHumidifier
from .devices.light_strip import SwitchbotLightStrip
from .devices.lock import SwitchbotLock
from .devices.plug import SwitchbotPlugMini
from .devices.relay_switch import SwitchbotRelaySwitch
from .discovery import GetSwitchbotDevices
from .models import SwitchBotAdvertisement

__all__ = [
    "get_device",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "parse_advertisement_data",
    "GetSwitchbotDevices",
    "SwitchBotAdvertisement",
    "SwitchbotAccountConnectionError",
    "SwitchbotApiError",
    "SwitchbotAuthenticationError",
    "SwitchbotEncryptedDevice",
    "ColorMode",
    "LockStatus",
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
    "SwitchbotLock",
    "SwitchbotBlindTilt",
    "SwitchbotRelaySwitch",
]
