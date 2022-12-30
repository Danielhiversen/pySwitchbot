"""Library to handle connection with Switchbot."""
from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypedDict

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parsers.bot import process_wohand
from .adv_parsers.bulb import process_color_bulb
from .adv_parsers.ceiling_light import process_woceiling
from .adv_parsers.contact import process_wocontact
from .adv_parsers.curtain import process_wocurtain
from .adv_parsers.humidifier import process_wohumidifier
from .adv_parsers.light_strip import process_wostrip
from .adv_parsers.lock import process_wolock
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
MFR_DATA_ORDER = (2409, 741, 89)


class SwitchbotSupportedType(TypedDict):
    """Supported type of Switchbot."""

    modelName: SwitchbotModel
    modelFriendlyName: str
    func: Callable[[bytes, bytes | None], dict[str, bool | int]]
    manufacturer_id: int | None
    manufacturer_data_length: int | None


SUPPORTED_TYPES: dict[str, SwitchbotSupportedType] = {
    "d": {
        "modelName": SwitchbotModel.CONTACT_SENSOR,
        "modelFriendlyName": "Contact Sensor",
        "func": process_wocontact,
        "manufacturer_id": 2409,
        "manufacturer_data_length": 13,
    },
    "H": {
        "modelName": SwitchbotModel.BOT,
        "modelFriendlyName": "Bot",
        "func": process_wohand,
        "service_uuids": {"cba20d00-224d-11e6-9fb8-0002a5d5c51b"},
        "manufacturer_id": 89,
    },
    "s": {
        "modelName": SwitchbotModel.MOTION_SENSOR,
        "modelFriendlyName": "Motion Sensor",
        "func": process_wopresence,
        "manufacturer_id": 2409,
    },
    "r": {
        "modelName": SwitchbotModel.LIGHT_STRIP,
        "modelFriendlyName": "Light Strip",
        "func": process_wostrip,
        "manufacturer_id": 2409,
        "manufacturer_data_length": 16,
    },
    "c": {
        "modelName": SwitchbotModel.CURTAIN,
        "modelFriendlyName": "Curtain",
        "func": process_wocurtain,
        "manufacturer_id": 2409,
    },
    "i": {
        "modelName": SwitchbotModel.METER,
        "modelFriendlyName": "Meter Plus",
        "func": process_wosensorth,
        "manufacturer_id": 2409,
    },
    "T": {
        "modelName": SwitchbotModel.METER,
        "modelFriendlyName": "Meter",
        "func": process_wosensorth,
        "manufacturer_id": 2409,
    },
    "g": {
        "modelName": SwitchbotModel.PLUG_MINI,
        "modelFriendlyName": "Plug Mini",
        "func": process_woplugmini,
        "manufacturer_data_length": 12,
        "manufacturer_id": 2409,
    },
    "j": {
        "modelName": SwitchbotModel.PLUG_MINI,
        "modelFriendlyName": "Plug Mini (JP)",
        "func": process_woplugmini,
        "manufacturer_id": 2409,
    },
    "u": {
        "modelName": SwitchbotModel.COLOR_BULB,
        "modelFriendlyName": "Color Bulb",
        "func": process_color_bulb,
        "manufacturer_id": 2409,
    },
    "q": {
        "modelName": SwitchbotModel.CEILING_LIGHT,
        "modelFriendlyName": "Ceiling Light",
        "func": process_woceiling,
        "manufacturer_id": 2409,
    },
    "e": {
        "modelName": SwitchbotModel.HUMIDIFIER,
        "modelFriendlyName": "Humidifier",
        "func": process_wohumidifier,
        "manufacturer_id": 741,
        "manufacturer_data_length": 6,
    },
    "o": {
        "modelName": SwitchbotModel.LOCK,
        "modelFriendlyName": "Lock",
        "func": process_wolock,
        "manufacturer_id": 2409,
    },
}

_SWITCHBOT_MODEL_TO_CHAR = {
    model_data["modelName"]: model_chr
    for model_chr, model_data in SUPPORTED_TYPES.items()
}

MODELS_BY_MANUFACTURER_DATA: dict[int, list[tuple[str, SwitchbotSupportedType]]] = {
    mfr_id: [] for mfr_id in MFR_DATA_ORDER
}
for model_chr, model in SUPPORTED_TYPES.items():
    if "manufacturer_id" in model:
        mfr_id = model["manufacturer_id"]
        MODELS_BY_MANUFACTURER_DATA[mfr_id].append((model_chr, model))


def parse_advertisement_data(
    device: BLEDevice,
    advertisement_data: AdvertisementData,
    model: SwitchbotModel | None = None,
) -> SwitchBotAdvertisement | None:
    """Parse advertisement data."""
    service_data = advertisement_data.service_data

    _service_data = None
    for uuid in SERVICE_DATA_ORDER:
        if uuid in service_data:
            _service_data = service_data[uuid]
            break

    _mfr_data = None
    _mfr_id = None
    for mfr_id in MFR_DATA_ORDER:
        if mfr_id in advertisement_data.manufacturer_data:
            _mfr_id = mfr_id
            _mfr_data = advertisement_data.manufacturer_data[mfr_id]
            break

    if _mfr_data is None and _service_data is None:
        return None

    try:
        data = _parse_data(
            _service_data,
            _mfr_data,
            _mfr_id,
            model,
        )
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception(
            "Failed to parse advertisement data: %s: %s", advertisement_data, err
        )
        return None

    if not data:
        return None

    return SwitchBotAdvertisement(
        device.address, data, device, advertisement_data.rssi, bool(_service_data)
    )


@lru_cache(maxsize=128)
def _parse_data(
    _service_data: bytes | None,
    _mfr_data: bytes | None,
    _mfr_id: int | None = None,
    _switchbot_model: SwitchbotModel | None = None,
) -> dict[str, Any] | None:
    """Parse advertisement data."""
    _model = chr(_service_data[0] & 0b01111111) if _service_data else None

    if _switchbot_model and _switchbot_model in _SWITCHBOT_MODEL_TO_CHAR:
        _model = _SWITCHBOT_MODEL_TO_CHAR[_switchbot_model]

    if not _model and _mfr_id and _mfr_id in MODELS_BY_MANUFACTURER_DATA:
        for model_chr, model_data in MODELS_BY_MANUFACTURER_DATA[_mfr_id]:
            if model_data.get("manufacturer_data_length") == len(_mfr_data):
                _model = model_chr
                break

    if not _model:
        return None

    _isEncrypted = bool(_service_data[0] & 0b10000000) if _service_data else False
    data = {
        "rawAdvData": _service_data,
        "data": {},
        "model": _model,
        "isEncrypted": _isEncrypted,
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
