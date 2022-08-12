"""Library to handle connection with Switchbot."""
from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parsers.bot import process_wohand
from .adv_parsers.bulb import process_color_bulb
from .adv_parsers.contact import process_wocontact
from .adv_parsers.curtain import process_wocurtain
from .adv_parsers.meter import process_wosensorth
from .adv_parsers.motion import process_wopresence
from .adv_parsers.plug import process_woplugmini
from .const import SwitchbotModel
from .models import SwitchBotAdvertisement


class SwitchbotSupportedType(TypedDict):
    """Supported type of Switchbot."""

    modelName: SwitchbotModel
    modelFriendlyName: str
    func: Callable[[bytes, bytes | None], dict[str, bool | int]]


SUPPORTED_TYPES: dict[str, SwitchbotSupportedType] = {
    "d": {
        "modelName": SwitchbotModel.CONTACT_SENSOR,
        "modelFriendlyName": "Contact Sensor",
        "func": process_wocontact,
    },
    "H": {
        "modelName": SwitchbotModel.BOT,
        "modelFriendlyName": "Bot",
        "func": process_wohand,
    },
    "s": {
        "modelName": SwitchbotModel.MOTION_SENSOR,
        "modelFriendlyName": "Motion Sensor",
        "func": process_wopresence,
    },
    "c": {
        "modelName": SwitchbotModel.CURTAIN,
        "modelFriendlyName": "Curtain",
        "func": process_wocurtain,
    },
    "T": {
        "modelName": SwitchbotModel.METER,
        "modelFriendlyName": "Meter",
        "func": process_wosensorth,
    },
    "i": {
        "modelName": SwitchbotModel.METER,
        "modelFriendlyName": "Meter Plus",
        "func": process_wosensorth,
    },
    "g": {
        "modelName": SwitchbotModel.PLUG_MINI,
        "modelFriendlyName": "Plug Mini",
        "func": process_woplugmini,
    },
    "u": {
        "modelName": SwitchbotModel.COLOR_BULB,
        "modelFriendlyName": "Color Bulb",
        "func": process_color_bulb,
    },
}


def parse_advertisement_data(
    device: BLEDevice, advertisement_data: AdvertisementData
) -> SwitchBotAdvertisement | None:
    """Parse advertisement data."""
    _services = list(advertisement_data.service_data.values())
    _mgr_datas = list(advertisement_data.manufacturer_data.values())

    if not _services:
        return None
    _service_data = _services[0]
    if not _service_data:
        return None
    _mfr_data = _mgr_datas[0] if _mgr_datas else None
    _model = chr(_service_data[0] & 0b01111111)

    data = {
        "address": device.address,  # MacOS uses UUIDs
        "rawAdvData": list(advertisement_data.service_data.values())[0],
        "data": {},
    }

    type_data = SUPPORTED_TYPES.get(_model)
    if type_data:
        data.update(
            {
                "isEncrypted": bool(_service_data[0] & 0b10000000),
                "model": _model,
                "modelFriendlyName": type_data["modelFriendlyName"],
                "modelName": type_data["modelName"],
                "data": type_data["func"](_service_data, _mfr_data),
            }
        )

    data["data"]["rssi"] = device.rssi

    return SwitchBotAdvertisement(device.address, data, device)
