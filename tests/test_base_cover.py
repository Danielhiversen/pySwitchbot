from unittest.mock import AsyncMock, Mock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import base_cover, blind_tilt

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(position=50, calibration=True):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    base_cover_device = base_cover.SwitchbotBaseCover(False, ble_device)
    base_cover_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, position, calibration)
    )
    base_cover_device._send_multiple_commands = AsyncMock()
    base_cover_device.update = AsyncMock()
    return base_cover_device


def make_advertisement_data(
    ble_device: BLEDevice, in_motion: bool, position: int, calibration: bool = True
):
    """Set advertisement data with defaults."""

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0X\x00\x11\x04",
            "data": {
                "calibration": calibration,
                "battery": 88,
                "inMotion": in_motion,
                "tilt": position,
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


@pytest.mark.asyncio
async def test_send_multiple_commands():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    base_cover_device = base_cover.SwitchbotBaseCover(False, ble_device)
    base_cover_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 50, True)
    )
    base_cover_device._send_command = AsyncMock()
    base_cover_device._check_command_result = Mock(return_value=True)
    await base_cover_device._send_multiple_commands(blind_tilt.OPEN_KEYS)
    assert base_cover_device._send_command.await_count == 2


@pytest.mark.asyncio
async def test_stop():
    base_cover_device = create_device_for_command_testing()
    await base_cover_device.stop()
    base_cover_device._send_multiple_commands.assert_awaited_once_with(
        base_cover.STOP_KEYS
    )


@pytest.mark.asyncio
async def test_set_position():
    base_cover_device = create_device_for_command_testing()
    await base_cover_device.set_position(50)
    base_cover_device._send_multiple_commands.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("data_value", [(None), (b"\x07"), (b"\x00")])
async def test_get_extended_info_adv_returns_none_when_bad_data(data_value):
    base_cover_device = create_device_for_command_testing()
    base_cover_device._send_command = AsyncMock(return_value=data_value)
    assert await base_cover_device.get_extended_info_adv() is None


@pytest.mark.asyncio
async def test_get_extended_info_adv_returns_single_device():
    base_cover_device = create_device_for_command_testing()
    base_cover_device._send_command = AsyncMock(
        return_value=bytes([0, 50, 20, 0, 0, 0, 0])
    )
    ext_result = await base_cover_device.get_extended_info_adv()
    assert ext_result["device0"]["battery"] == 50
    assert ext_result["device0"]["firmware"] == 2
    assert "device1" not in ext_result


@pytest.mark.asyncio
async def test_get_extended_info_adv_returns_both_devices():
    base_cover_device = create_device_for_command_testing()
    base_cover_device._send_command = AsyncMock(
        return_value=bytes([0, 50, 20, 0, 10, 30, 0])
    )
    ext_result = await base_cover_device.get_extended_info_adv()
    assert ext_result["device0"]["battery"] == 50
    assert ext_result["device0"]["firmware"] == 2
    assert ext_result["device1"]["battery"] == 10
    assert ext_result["device1"]["firmware"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_value,result",
    [
        (0, "not_charging"),
        (1, "charging_by_adapter"),
        (2, "charging_by_solar"),
        (3, "fully_charged"),
        (4, "solar_not_charging"),
        (5, "charging_error"),
    ],
)
async def test_get_extended_info_adv_returns_device0_charge_states(data_value, result):
    base_cover_device = create_device_for_command_testing()
    base_cover_device._send_command = AsyncMock(
        return_value=bytes([0, 50, 20, data_value, 10, 30, 0])
    )
    ext_result = await base_cover_device.get_extended_info_adv()
    assert ext_result["device0"]["stateOfCharge"] == result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_value,result",
    [
        (0, "not_charging"),
        (1, "charging_by_adapter"),
        (2, "charging_by_solar"),
        (3, "fully_charged"),
        (4, "solar_not_charging"),
        (5, "charging_error"),
    ],
)
async def test_get_extended_info_adv_returns_device1_charge_states(data_value, result):
    base_cover_device = create_device_for_command_testing()
    base_cover_device._send_command = AsyncMock(
        return_value=bytes([0, 50, 20, 0, 10, 30, data_value])
    )
    ext_result = await base_cover_device.get_extended_info_adv()
    assert ext_result["device1"]["stateOfCharge"] == result
