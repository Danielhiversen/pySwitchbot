"""Library to handle connection with Switchbot."""
from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import TypedDict

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parsers.bot import process_wohand
from .adv_parsers.bulb import process_color_bulb
from .adv_parsers.ceiling_light import process_woceiling
from .adv_parsers.contact import process_wocontact
from .adv_parsers.curtain import process_wocurtain
from .adv_parsers.humidifier import process_wohumidifier
from .adv_parsers.light_strip import process_wostrip
from .adv_parsers.meter import process_wosensorth
from .adv_parsers.motion import process_wopresence
from .adv_parsers.plug import process_woplugmini
from .const import SwitchbotModel
from .models import SwitchBotAdvertisement

_LOGGER = logging.getLogger(__name__)

SERVICE_DATA_ORDER = (
    "0000fd3d-0000-1000-8000-00805f9b34fb",
    "00000d00-0000-1000-8000-00805f9b34fb",
)


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
    "r": {
        "modelName": SwitchbotModel.LIGHT_STRIP,
        "modelFriendlyName": "Light Strip",
        "func": process_wostrip,
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
    "q": {
        "modelName": SwitchbotModel.CEILING_LIGHT,
        "modelFriendlyName": "Ceiling Light",
        "func": process_woceiling,
    },
    "e": {
        "modelName": SwitchbotModel.HUMIDIFIER,
        "modelFriendlyName": "Humidifier",
        "func": process_wohumidifier,
    },
}


def parse_advertisement_data(
    device: BLEDevice, advertisement_data: AdvertisementData
) -> SwitchBotAdvertisement | None:
    """Parse advertisement data."""
    _mgr_datas = list(advertisement_data.manufacturer_data.values())
    service_data = advertisement_data.service_data

    if not service_data:
        return None

    _service_data = None
    for uuid in SERVICE_DATA_ORDER:
        if uuid in service_data:
            _service_data = service_data[uuid]
            break

    if not _service_data:
        return None

    _mfr_data = _mgr_datas[0] if _mgr_datas else None

    try:
        data = _parse_data(_service_data, _mfr_data)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception(
            "Failed to parse advertisement data: %s: %s", advertisement_data, err
        )
        return None

    return SwitchBotAdvertisement(device.address, data, device, advertisement_data.rssi)


@lru_cache(maxsize=128)
def _parse_data(
    _service_data: bytes, _mfr_data: bytes | None
) -> SwitchBotAdvertisement | None:
    """Parse advertisement data."""
    _model = chr(_service_data[0] & 0b01111111)
    data = {
        "rawAdvData": _service_data,
        "data": {},
        "model": _model,
        "isEncrypted": bool(_service_data[0] & 0b10000000),
    }

    type_data = SUPPORTED_TYPES.get(_model)
    if type_data:
        model_data = type_data["func"](_service_data, _mfr_data)
        if model_data:
            data.update(
                {
                    "modelFriendlyName": type_data["modelFriendlyName"],
                    "modelName": type_data["modelName"],
                    "data": model_data,
                }
            )

    return data
