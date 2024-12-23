from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import relay_switch

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(calibration=True, reverse_mode=False):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    relay_switch_device = relay_switch.SwitchbotRelaySwitch(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff"
    )
    relay_switch_device.update_from_advertisement(make_advertisement_data(ble_device))
    return relay_switch_device


def make_advertisement_data(ble_device: BLEDevice):
    """Set advertisement data with defaults."""

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"$X|\x0866G\x81\x00\x00\x001\x00\x00\x00\x00",
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
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_turn_on():
    relay_switch_device = create_device_for_command_testing()
    relay_switch_device._send_command = AsyncMock(return_value=b"\x01")
    await relay_switch_device.turn_on()
    assert relay_switch_device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    relay_switch_device = create_device_for_command_testing()
    relay_switch_device._send_command = AsyncMock(return_value=b"\x01")
    await relay_switch_device.turn_off()
    assert relay_switch_device.is_on() is False


@pytest.mark.asyncio
async def test_get_basic_info():
    relay_switch_device = create_device_for_command_testing()
    relay_switch_device._send_command = AsyncMock(return_value=b"\x01\x01")
    info = await relay_switch_device.get_basic_info()
    assert info["is_on"] is True
    relay_switch_device._send_command = AsyncMock(return_value=b"\x01\x00")
    info = await relay_switch_device.get_basic_info()
    assert info["is_on"] is False
    relay_switch_device._send_command = AsyncMock(return_value=b"\x00\x00")
    info = await relay_switch_device.get_basic_info()
    assert info is None
