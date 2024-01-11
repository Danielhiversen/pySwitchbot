from typing import Any
from unittest.mock import Mock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import curtain

from .test_adv_parser import generate_ble_device


def set_advertisement_data(ble_device: BLEDevice, in_motion: bool, position: int):
    """Set advertisement data with defaults."""

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0X\x00\x11\x04",
            "data": {
                "calibration": True,
                "battery": 88,
                "inMotion": in_motion,
                "position": position,
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


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_not_in_motion(reverse_mode):
    """Test passive not in motion advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, False, 0)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening(reverse_mode):
    """Test passive opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 10)
    )

    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing(reverse_mode):
    """Test passive closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening_then_stop(reverse_mode):
    """Test passive stopped after opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 10)
    )
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, False, 10)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing_then_stop(reverse_mode):
    """Test passive stopped after closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 90)
    )
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, False, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_not_in_motion(reverse_mode):
    """Test active not in motion."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, False, 0)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 0, 100, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_opening(reverse_mode):
    """Test active opening."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 0)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 10, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_closing(reverse_mode):
    """Test active closing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 100)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 90, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_opening_then_stop(reverse_mode):
    """Test active stopped after opening."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 0)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 10, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    basic_info = bytes([0, 0, 0, 0, 0, 0, 10, 0])

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_closing_then_stop(reverse_mode):
    """Test active stopped after closing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        set_advertisement_data(ble_device, True, 100)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 90, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    basic_info = bytes([0, 0, 0, 0, 0, 0, 90, 0])

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False
