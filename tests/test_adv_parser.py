from typing import Any

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from switchbot import SwitchbotModel
from switchbot.adv_parser import parse_advertisement_data
from switchbot.models import SwitchBotAdvertisement

ADVERTISEMENT_DATA_DEFAULTS = {
    "local_name": "",
    "manufacturer_data": {},
    "service_data": {},
    "service_uuids": [],
    "rssi": -127,
    "platform_data": ((),),
    "tx_power": -127,
}


def generate_advertisement_data(**kwargs: Any) -> AdvertisementData:
    """Generate advertisement data with defaults."""
    new = kwargs.copy()
    for key, value in ADVERTISEMENT_DATA_DEFAULTS.items():
        new.setdefault(key, value)
    return AdvertisementData(**new)


def test_parse_advertisement_data_curtain():
    """Test parse_advertisement_data for curtain."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0X\x00\x11\x04"},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0X\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 88,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
    )


def test_parse_advertisement_data_curtain_position_zero():
    """Test parse_advertisement_data for curtain position zero."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={89: b"\xc1\xc7'}U\xab"},
        service_data={"00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0\xced\x11\x04"},
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-52,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xd0\xced\x11\x04",
            "data": {
                "calibration": True,
                "battery": 78,
                "inMotion": False,
                "position": 0,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-52,
    )


def test_parse_advertisement_data_curtain_firmware_six_position_100():
    """Test parse_advertisement_data with firmware six for curtain position 100."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xf5\x98\x94\x08\xa0\xe7",
            2409: b'\xf5\x98\x94\x08\xa0\xe7\x9b\x0f\x00"\x04',
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0H\x00\x12\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b'c\xc0G\x00"\x04',
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-62,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xd0H\x00\x12\x04",
            "data": {
                "calibration": True,
                "battery": 72,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-62,
    )


def test_parse_advertisement_data_curtain_firmware_six_position_100_other_rssi():
    """Test parse_advertisement_data with firmware six for curtain position 100 other rssi."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xf5\x98\x94\x08\xa0\xe7",
            2409: b'\xf5\x98\x94\x08\xa0\xe7\xa5\x0fc"\x04',
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0H\x00\x12\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b'c\xc0Gc"\x04',
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xd0H\x00\x12\x04",
            "data": {
                "calibration": True,
                "battery": 72,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-67,
    )


def test_parse_advertisement_data_curtain_fully_closed():
    """Test parse_advertisement_data with firmware six fully closed."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={2409: b"\xc1\xc7'}U\xab\"\x0fd\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0Sd\x11\x04"},
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=1,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0Sd\x11\x04",
            "data": {
                "calibration": True,
                "battery": 83,
                "inMotion": False,
                "position": 0,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=1,
    )


def test_parse_advertisement_data_curtain_fully_open():
    """Test parse_advertisement_data with firmware six fully open."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={2409: b"\xc1\xc7'}U\xab%\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0S\x00\x11\x04"},
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=1,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0S\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 83,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=1,
    )


def test_parse_advertisement_data_contact():
    """Test parse_advertisement_data for the contact sensor."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d@d\x05\x00u\x00\xf8\x12"
        },
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"d@d\x05\x00u\x00\xf8\x12",
            "data": {
                "button_count": 2,
                "contact_open": True,
                "contact_timeout": True,
                "is_light": True,
                "battery": 100,
                "motion_detected": True,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
        },
        device=ble_device,
        rssi=-80,
    )


def test_parse_advertisement_data_empty():
    """Test parse_advertisement_data with empty data does not blow up."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b""},
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result is None


def test_new_bot_firmware():
    """Test parsing adv data from new bot firmware."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={89: b"\xd8.\xad\xcd\r\x85"},
        service_data={"00000d00-0000-1000-8000-00805f9b34fb": b"H\x10\xe1"},
        service_uuids=["CBA20D00-224D-11E6-9FB8-0002A5D5C51B"],
        rssi=-90,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"H\x10\xe1",
            "data": {"switchMode": False, "isOn": False, "battery": 97},
            "model": "H",
            "isEncrypted": False,
            "modelFriendlyName": "Bot",
            "modelName": SwitchbotModel.BOT,
        },
        device=ble_device,
        rssi=-90,
    )
