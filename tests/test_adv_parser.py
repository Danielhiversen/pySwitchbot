from switchbot.adv_parser import parse_advertisement_data
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice

from switchbot.models import SwitchBotAdvertisement


def test_parse_advertisement_data_curtain():
    """Test parse_advertisement_data for curtain."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = AdvertisementData(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b"c\xc0X\x00\x11\x04"},
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result == SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "address": "aa:bb:cc:dd:ee:ff",
            "rawAdvData": b"c\xc0X\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 88,
                "inMotion": False,
                "position": 100,
                "lightLevel": 1,
                "deviceChain": 1,
                "rssi": 0,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": "WoCurtain",
        },
        device=ble_device,
    )


def test_parse_advertisement_data_empty():
    """Test parse_advertisement_data with empty data does not blow up."""
    ble_device = BLEDevice("aa:bb:cc:dd:ee:ff", "any")
    adv_data = AdvertisementData(
        manufacturer_data={2409: b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"},
        service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": b""},
    )
    result = parse_advertisement_data(ble_device, adv_data)
    assert result is None