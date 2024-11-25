from __future__ import annotations

from typing import Any

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from switchbot import LockStatus, SwitchbotModel
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

BLE_DEVICE_DEFAULTS = {
    "name": None,
    "rssi": -127,
    "details": None,
}


def generate_ble_device(
    address: str | None = None,
    name: str | None = None,
    details: Any | None = None,
    rssi: int | None = None,
    **kwargs: Any,
) -> BLEDevice:
    """Generate a BLEDevice with defaults."""
    new = kwargs.copy()
    if address is not None:
        new["address"] = address
    if name is not None:
        new["name"] = name
    if details is not None:
        new["details"] = details
    if rssi is not None:
        new["rssi"] = rssi
    for key, value in BLE_DEVICE_DEFAULTS.items():
        new.setdefault(key, value)
    return BLEDevice(**new)


def generate_advertisement_data(**kwargs: Any) -> AdvertisementData:
    """Generate advertisement data with defaults."""
    new = kwargs.copy()
    for key, value in ADVERTISEMENT_DATA_DEFAULTS.items():
        new.setdefault(key, value)
    return AdvertisementData(**new)


def test_parse_advertisement_data_curtain():
    """Test parse_advertisement_data for curtain."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
        active=True,
    )


def test_parse_advertisement_data_curtain_passive():
    """Test parse_advertisement_data for curtain passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "calibration": None,
                "battery": None,
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
        active=False,
    )


def test_parse_advertisement_data_curtain_passive_12_bytes():
    """Test parse_advertisement_data for curtain passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04\x00"},
        service_data={},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "calibration": None,
                "battery": None,
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
        active=False,
    )


def test_parse_advertisement_data_curtain_position_zero():
    """Test parse_advertisement_data for curtain position zero."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_position_100():
    """Test parse_advertisement_data with firmware six for curtain position 100."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
            "rawAdvData": b'c\xc0G\x00"\x04',
            "data": {
                "calibration": True,
                "battery": 71,
                "inMotion": False,
                "position": 100,
                "lightLevel": 2,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-62,
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_position_100_other_rssi():
    """Test parse_advertisement_data with firmware six for curtain position 100 other rssi."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
            "rawAdvData": b'c\xc0Gc"\x04',
            "data": {
                "calibration": True,
                "battery": 71,
                "inMotion": False,
                "position": 1,
                "lightLevel": 2,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parse_advertisement_data_curtain_fully_closed():
    """Test parse_advertisement_data with firmware six fully closed."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
        active=True,
    )


def test_parse_advertisement_data_curtain_fully_open():
    """Test parse_advertisement_data with firmware six fully open."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
        active=True,
    )


def test_parse_advertisement_data_curtain3():
    """Test parse_advertisement_data for curtain 3."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xaa\xbb\xcc\xdd\xee\xff\xf7\x07\x00\x11\x04\x00\x49"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"{\xc0\x49\x00\x11\x04"},
        rssi=-80,
    )

    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"{\xc0\x49\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 73,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "{",
            "modelFriendlyName": "Curtain 3",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def test_parse_advertisement_data_curtain3_passive():
    """Test parse_advertisement_data for curtain passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xaa\xbb\xcc\xdd\xee\xff\xf7\x07\x00\x11\x04\x00\x49"
        },
        service_data={},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": None,
            "data": {
                "calibration": None,
                "battery": 73,
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
        active=False,
    )


def test_parse_advertisement_data_contact():
    """Test parse_advertisement_data for the contact sensor."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
        active=True,
    )


def test_parse_advertisement_data_empty():
    """Test parse_advertisement_data with empty data does not blow up."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2403: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b""},
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result is None


def test_new_bot_firmware():
    """Test parsing adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
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
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_fully_closed():
    """Test parse_advertisement_data with firmware six fully closed."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xcc\xf4\xc4\xf9\xacl",
            2409: b"\xcc\xf4\xc4\xf9\xacl\xeb\x0fd\x12\x04",
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0Yd\x11\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0dd\x12\x04",
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-2,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0dd\x12\x04",
            "data": {
                "calibration": True,
                "battery": 100,
                "inMotion": False,
                "position": 0,
                "lightLevel": 1,
                "deviceChain": 2,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-2,
        active=True,
    )


def test_parse_advertisement_data_curtain_firmware_six_fully_open():
    """Test parse_advertisement_data with firmware six fully open."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        local_name="WoCurtain",
        manufacturer_data={
            89: b"\xcc\xf4\xc4\xf9\xacl",
            2409: b"\xcc\xf4\xc4\xf9\xacl\xe2\x0f\x00\x12\x04",
        },
        service_data={
            "00000d00-0000-1000-8000-00805f9b34fb": b"c\xd0Yd\x11\x04",
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0d\x00\x12\x04",
        },
        service_uuids=[
            "00001800-0000-1000-8000-00805f9b34fb",
            "00001801-0000-1000-8000-00805f9b34fb",
            "cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        ],
        rssi=-2,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0d\x00\x12\x04",
            "data": {
                "calibration": True,
                "battery": 100,
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
        rssi=-2,
        active=True,
    )


def test_contact_sensor_mfr():
    """Test parsing adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=FA,\x00F\x01\x8f\xc4"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d\x00\xda\x04\x00F\x01\x8f\xc4"
        },
        tx_power=-127,
        rssi=-70,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": True,
                "contact_timeout": True,
                "is_light": False,
                "motion_detected": False,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d\x00\xda\x04\x00F\x01\x8f\xc4",
        },
        device=ble_device,
        rssi=-70,
        active=True,
    )


def test_contact_sensor_mfr_no_service_data():
    """Test contact sensor with passive data only."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=FA,\x00F\x01\x8f\xc4"},
        service_data={},
        tx_power=-127,
        rssi=-70,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    # Passive detection of contact sensor is not supported
    # anymore since the Switchbot Curtain v3 was released
    # which uses the heuristics for the contact sensor.
    assert result is None


def test_contact_sensor_srv():
    """Test parsing adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d\x00\xda\x04\x00F\x01\x8f\xc4"
        },
        tx_power=-127,
        rssi=-70,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": True,
                "contact_timeout": True,
                "is_light": False,
                "motion_detected": False,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d\x00\xda\x04\x00F\x01\x8f\xc4",
        },
        device=ble_device,
        rssi=-70,
        active=True,
    )


def test_contact_sensor_open():
    """Test parsing mfr adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=F\x84\x9c\x00\x17\x00QD"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d@\xda\x02\x00\x17\x00QD"
        },
        tx_power=-127,
        rssi=-59,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": True,
                "contact_timeout": False,
                "is_light": False,
                "motion_detected": True,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d@\xda\x02\x00\x17\x00QD",
        },
        device=ble_device,
        rssi=-59,
        active=True,
    )


def test_contact_sensor_closed():
    """Test parsing mfr adv data from new bot firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xcb9\xcd\xc4=F\x89\x8c\x00+\x00\x19\x84"},
        service_data={
            "0000fd3d-0000-1000-8000-00805f9b34fb": b"d@\xda\x00\x00+\x00\x19\x84"
        },
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 90,
                "button_count": 4,
                "contact_open": False,
                "contact_timeout": False,
                "is_light": False,
                "motion_detected": True,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "d",
            "modelFriendlyName": "Contact Sensor",
            "modelName": SwitchbotModel.CONTACT_SENSOR,
            "rawAdvData": b"d@\xda\x00\x00+\x00\x19\x84",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_switchbot_passive():
    """Test parsing switchbot as passive."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={89: bytes.fromhex("d51cfb397856")},
        service_data={},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.BOT)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "switchMode": None,
                "isOn": None,
            },
            "isEncrypted": False,
            "model": "H",
            "modelFriendlyName": "Bot",
            "modelName": SwitchbotModel.BOT,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-50,
        active=False,
    )


def test_bulb_active():
    """Test parsing bulb as active."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\x84\xf7\x03\xb4\xcbz\x03\xe4!\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"u\x00d"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "brightness": 100,
                "color_mode": 1,
                "delay": False,
                "isOn": True,
                "loop_index": 0,
                "preset": False,
                "sequence_number": 3,
                "speed": 0,
            },
            "isEncrypted": False,
            "model": "u",
            "modelFriendlyName": "Color Bulb",
            "modelName": SwitchbotModel.COLOR_BULB,
            "rawAdvData": b"u\x00d",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wosensor_passive_and_active():
    """Test parsing wosensor as passive with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xd7\xc1}]\xebC\xde\x03\x06\x985"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"T\x00\xe4\x06\x985"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "T",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER,
            "rawAdvData": b"T\x00\xe4\x06\x985",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wosensor_active():
    """Test parsing wosensor with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"T\x00\xe4\x06\x985"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "T",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER,
            "rawAdvData": b"T\x00\xe4\x06\x985",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wosensor_passive_only():
    """Test parsing wosensor with only passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xd7\xc1}]\xebC\xde\x03\x06\x985"},
        service_data={},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.METER)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "T",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-50,
        active=False,
    )


def test_wosensor_active_zero_data():
    """Test parsing wosensor with active data but all values are zero."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"T\x00\x00\x00\x00\x00"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {},
            "isEncrypted": False,
            "model": "T",
            "rawAdvData": b"T\x00\x00\x00\x00\x00",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_wohub2_passive_and_active():
    """Test parsing wosensor as passive with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xaa\xbb\xcc\xdd\xee\xff\x00\xfffT\x1a\xf1\x82\x07\x9a2\x00"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"v\x00"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "fahrenheit": False,
                "humidity": 50,
                "lightLevel": 2,
                "temp": {"c": 26.7, "f": 80.06},
                "temperature": 26.7,
            },
            "isEncrypted": False,
            "model": "v",
            "modelFriendlyName": "Hub 2",
            "modelName": SwitchbotModel.HUB2,
            "rawAdvData": b"v\x00",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_woiosensor_passive_and_active():
    """Test parsing woiosensor as passive with active data as well."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xaa\xbb\xcc\xdd\xee\xff\xe0\x0f\x06\x985\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"w\x00\xe4"},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "w",
            "modelFriendlyName": "Indoor/Outdoor Meter",
            "modelName": SwitchbotModel.IO_METER,
            "rawAdvData": b"w\x00\xe4",
        },
        device=ble_device,
        rssi=-50,
        active=True,
    )


def test_woiosensor_passive_only():
    """Test parsing woiosensor with only passive data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xaa\xbb\xcc\xdd\xee\xff\xe0\x0f\x06\x985\x00"},
        service_data={},
        tx_power=-127,
        rssi=-50,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.IO_METER)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": False,
                "humidity": 53,
                "temp": {"c": 24.6, "f": 76.28},
                "temperature": 24.6,
            },
            "isEncrypted": False,
            "model": "w",
            "modelFriendlyName": "Indoor/Outdoor Meter",
            "modelName": SwitchbotModel.IO_METER,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-50,
        active=False,
    )


def test_motion_sensor_clear():
    """Test parsing motion sensor with clear data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIj\x1c\x00f"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s\x00\xe2\x00f\x01"},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": False,
                "led": 0,
                "light_intensity": 1,
                "motion_detected": False,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s\x00\xe2\x00f\x01",
        },
        device=ble_device,
        rssi=-87,
        active=True,
    )


def test_motion_sensor_clear_passive():
    """Test parsing motion sensor with clear data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIj\x1c\x00f"},
        service_data={},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "iot": None,
                "is_light": False,
                "led": None,
                "light_intensity": None,
                "motion_detected": False,
                "sense_distance": None,
                "tested": None,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-87,
        active=False,
    )


def test_motion_sensor_motion():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIi\\\x008"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s@\xe2\x008\x01"},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": False,
                "led": 0,
                "light_intensity": 1,
                "motion_detected": True,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s@\xe2\x008\x01",
        },
        device=ble_device,
        rssi=-87,
        active=True,
    )


def test_motion_sensor_motion_passive():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIi\\\x008"},
        service_data={},
        tx_power=-127,
        rssi=-87,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "iot": None,
                "is_light": False,
                "led": None,
                "light_intensity": None,
                "motion_detected": True,
                "sense_distance": None,
                "tested": None,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-87,
        active=False,
    )


def test_motion_sensor_is_light_passive():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIs,\x04g"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s\x00\xe2\x04g\x02"},
        tx_power=-127,
        rssi=-93,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": True,
                "led": 0,
                "light_intensity": 2,
                "motion_detected": False,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s\x00\xe2\x04g\x02",
        },
        device=ble_device,
        rssi=-93,
        active=True,
    )


def test_motion_sensor_is_light_active():
    """Test parsing motion sensor with motion data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s\x00\xe2\x04g\x02"},
        tx_power=-127,
        rssi=-93,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": True,
                "led": 0,
                "light_intensity": 2,
                "motion_detected": False,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s\x00\xe2\x04g\x02",
        },
        device=ble_device,
        rssi=-93,
        active=True,
    )


def test_motion_with_light_detected():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc0!\x9a\xe8\xbcIvl\x00,"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"s@\xe2\x00,\x02"},
        tx_power=-127,
        rssi=-84,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.MOTION_SENSOR
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 98,
                "iot": 0,
                "is_light": True,
                "led": 0,
                "light_intensity": 2,
                "motion_detected": True,
                "sense_distance": 0,
                "tested": False,
            },
            "isEncrypted": False,
            "model": "s",
            "modelFriendlyName": "Motion Sensor",
            "modelName": SwitchbotModel.MOTION_SENSOR,
            "rawAdvData": b"s@\xe2\x00,\x02",
        },
        device=ble_device,
        rssi=-84,
        active=True,
    )


def test_parsing_lock_active():
    """Test parsing lock with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xf1\t\x9fE\x1a]\x07\x83\x00 "},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"o\x80d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "auto_lock_paused": False,
                "battery": 100,
                "calibration": True,
                "door_open": False,
                "double_lock_mode": False,
                "night_latch": False,
                "status": LockStatus.LOCKED,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "update_from_secondary_lock": False,
            },
            "isEncrypted": False,
            "model": "o",
            "modelFriendlyName": "Lock",
            "modelName": SwitchbotModel.LOCK,
            "rawAdvData": b"o\x80d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parsing_lock_passive():
    """Test parsing lock with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xf1\t\x9fE\x1a]\x07\x83\x00 "}, rssi=-67
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LOCK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "auto_lock_paused": False,
                "battery": None,
                "calibration": True,
                "door_open": False,
                "double_lock_mode": False,
                "night_latch": False,
                "status": LockStatus.LOCKED,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "update_from_secondary_lock": False,
            },
            "isEncrypted": False,
            "model": "o",
            "modelFriendlyName": "Lock",
            "modelName": SwitchbotModel.LOCK,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_parsing_lock_pro_active():
    """Test parsing lock pro with active data."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xc8\xf5,\xd9-V\x07\x82\x00d\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"$\x80d"},
        rssi=-80,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LOCK_PRO)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "calibration": True,
                "status": LockStatus.LOCKED,
                "update_from_secondary_lock": False,
                "door_open": False,
                "double_lock_mode": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "model": "$",
            "isEncrypted": False,
            "modelFriendlyName": "Lock Pro",
            "modelName": SwitchbotModel.LOCK_PRO,
            "rawAdvData": b"$\x80d",
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


def test_parsing_lock_pro_passive():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: bytes.fromhex("aabbccddeeff208200640000")}, rssi=-67
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LOCK_PRO)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "calibration": True,
                "status": LockStatus.LOCKED,
                "update_from_secondary_lock": False,
                "door_open": False,
                "double_lock_mode": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "model": "$",
            "isEncrypted": False,
            "modelFriendlyName": "Lock Pro",
            "modelName": SwitchbotModel.LOCK_PRO,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_parsing_lock_pro_passive_nightlatch_disabled():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: bytes.fromhex("aabbccddeeff0a8200630000")}, rssi=-67
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LOCK_PRO)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "calibration": True,
                "status": LockStatus.LOCKED,
                "update_from_secondary_lock": False,
                "door_open": False,
                "double_lock_mode": False,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "auto_lock_paused": False,
                "night_latch": False,
            },
            "model": "$",
            "isEncrypted": False,
            "modelFriendlyName": "Lock Pro",
            "modelName": SwitchbotModel.LOCK_PRO,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_parsing_lock_active_old_firmware():
    """Test parsing lock with active data. Old firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xf1\t\x9fE\x1a]\x07\x83\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"o\x80d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "auto_lock_paused": False,
                "battery": 100,
                "calibration": True,
                "door_open": False,
                "double_lock_mode": False,
                "night_latch": False,
                "status": LockStatus.LOCKED,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "update_from_secondary_lock": False,
            },
            "isEncrypted": False,
            "model": "o",
            "modelFriendlyName": "Lock",
            "modelName": SwitchbotModel.LOCK,
            "rawAdvData": b"o\x80d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parsing_lock_passive_old_firmware():
    """Test parsing lock with active data. Old firmware."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xf1\t\x9fE\x1a]\x07\x83\x00"}, rssi=-67
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.LOCK)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "auto_lock_paused": False,
                "battery": None,
                "calibration": True,
                "door_open": False,
                "double_lock_mode": False,
                "night_latch": False,
                "status": LockStatus.LOCKED,
                "unclosed_alarm": False,
                "unlocked_alarm": False,
                "update_from_secondary_lock": False,
            },
            "isEncrypted": False,
            "model": "o",
            "modelFriendlyName": "Lock",
            "modelName": SwitchbotModel.LOCK,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_meter_pro_active() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeR\xdd\x84\x06d\x08\x97,\x00\x05"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"4\x00d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": False,
                "humidity": 44,
                "temp": {"c": 23.8, "f": 74.84},
                "temperature": 23.8,
            },
            "isEncrypted": False,
            "model": "4",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER_PRO,
            "rawAdvData": b"4\x00d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_meter_pro_passive() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xb0\xe9\xfeR\xdd\x84\x06d\x08\x97,\x00\x05"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.METER_PRO)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": False,
                "humidity": 44,
                "temp": {"c": 23.8, "f": 74.84},
                "temperature": 23.8,
            },
            "isEncrypted": False,
            "model": "4",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER_PRO,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_meter_pro_c_active() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xb0\xe9\xfeT2\x15\xb7\xe4\x07\x9b\xa4\x007\x02\xd5\x00"
        },
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"5\x00d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": 100,
                "fahrenheit": True,
                "humidity": 36,
                "temp": {"c": 27.7, "f": 81.86},
                "temperature": 27.7,
                "co2": 725,
            },
            "isEncrypted": False,
            "model": "5",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER_PRO_C,
            "rawAdvData": b"5\x00d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_meter_pro_c_passive() -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={
            2409: b"\xb0\xe9\xfeT2\x15\xb7\xe4\x07\x9b\xa4\x007\x02\xd5\x00"
        },
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.METER_PRO_C)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "battery": None,
                "fahrenheit": True,
                "humidity": 36,
                "temp": {"c": 27.7, "f": 81.86},
                "temperature": 27.7,
                "co2": 725,
            },
            "isEncrypted": False,
            "model": "5",
            "modelFriendlyName": "Meter",
            "modelName": SwitchbotModel.METER_PRO_C,
            "rawAdvData": None,
        },
        device=ble_device,
        rssi=-67,
        active=False,
    )


def test_parse_advertisement_data_keypad():
    """Test parse_advertisement_data for the keypad."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"\xeb\x13\x02\xe6#\x0f\x8fd\x00\x00\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"y\x00d"},
        rssi=-67,
    )
    result = parse_advertisement_data(ble_device, adv_data, SwitchbotModel.KEYPAD)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {"attempt_state": 143, "battery": 100},
            "isEncrypted": False,
            "model": "y",
            "modelFriendlyName": "Keypad",
            "modelName": SwitchbotModel.KEYPAD,
            "rawAdvData": b"y\x00d",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parse_advertisement_data_relay_switch_1pm():
    """Test parse_advertisement_data for the keypad."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"<\x00\x00\x00"},
        rssi=-67,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.RELAY_SWITCH_1PM
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "switchMode": True,
                "sequence_number": 71,
                "isOn": True,
                "power": 4.9,
                "voltage": 0,
                "current": 0,
            },
            "isEncrypted": False,
            "model": "<",
            "modelFriendlyName": "Relay Switch 1PM",
            "modelName": SwitchbotModel.RELAY_SWITCH_1PM,
            "rawAdvData": b"<\x00\x00\x00",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )


def test_parse_advertisement_data_relay_switch_1():
    """Test parse_advertisement_data for the keypad."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b";\x00\x00\x00"},
        rssi=-67,
    )
    result = parse_advertisement_data(
        ble_device, adv_data, SwitchbotModel.RELAY_SWITCH_1
    )
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "data": {
                "switchMode": True,
                "sequence_number": 71,
                "isOn": True,
            },
            "isEncrypted": False,
            "model": ";",
            "modelFriendlyName": "Relay Switch 1",
            "modelName": SwitchbotModel.RELAY_SWITCH_1,
            "rawAdvData": b";\x00\x00\x00",
        },
        device=ble_device,
        rssi=-67,
        active=True,
    )
