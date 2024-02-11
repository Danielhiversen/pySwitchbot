from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.devices import blind_tilt
from switchbot.devices.base_cover import COVER_EXT_SUM_KEY

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    position=50, calibration=True, reverse_mode=False
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = blind_tilt.SwitchbotBlindTilt(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, position, calibration)
    )
    curtain_device._send_multiple_commands = AsyncMock()
    curtain_device.update = AsyncMock()
    return curtain_device


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
async def test_open():
    blind_device = create_device_for_command_testing()
    await blind_device.open()
    blind_device._send_multiple_commands.assert_awaited_once_with(blind_tilt.OPEN_KEYS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "position,keys", [(5, blind_tilt.CLOSE_DOWN_KEYS), (55, blind_tilt.CLOSE_UP_KEYS)]
)
async def test_close(position, keys):
    blind_device = create_device_for_command_testing(position=position)
    await blind_device.close()
    blind_device._send_multiple_commands.assert_awaited_once_with(keys)


@pytest.mark.asyncio
async def test_get_basic_info_returns_none_when_no_data():
    blind_device = create_device_for_command_testing()
    blind_device._get_basic_info = AsyncMock(return_value=None)

    assert await blind_device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reverse_mode,data,result",
    [
        (
            False,
            bytes([0, 1, 10, 2, 255, 255, 50, 4]),
            [1, 1, 1, 1, 1, True, False, False, True, 50, 4],
        ),
        (
            False,
            bytes([0, 1, 10, 2, 0, 0, 50, 4]),
            [1, 1, 0, 0, 0, False, False, False, False, 50, 4],
        ),
        (
            False,
            bytes([0, 1, 10, 2, 0, 1, 50, 4]),
            [1, 1, 0, 0, 1, False, True, False, True, 50, 4],
        ),
        (
            True,
            bytes([0, 1, 10, 2, 255, 255, 50, 4]),
            [1, 1, 1, 1, 1, True, False, True, False, 50, 4],
        ),
        (
            True,
            bytes([0, 1, 10, 2, 0, 0, 50, 4]),
            [1, 1, 0, 0, 0, False, False, False, False, 50, 4],
        ),
        (
            True,
            bytes([0, 1, 10, 2, 0, 1, 50, 4]),
            [1, 1, 0, 0, 1, False, True, False, True, 50, 4],
        ),
    ],
)
async def test_get_basic_info(reverse_mode, data, result):
    blind_device = create_device_for_command_testing(reverse_mode=reverse_mode)
    blind_device._get_basic_info = AsyncMock(return_value=data)

    info = await blind_device.get_basic_info()
    assert info["battery"] == result[0]
    assert info["firmware"] == result[1]
    assert info["light"] == result[2]
    assert info["fault"] == result[2]
    assert info["solarPanel"] == result[3]
    assert info["calibration"] == result[3]
    assert info["calibrated"] == result[3]
    assert info["inMotion"] == result[4]
    assert info["motionDirection"]["opening"] == result[5]
    assert info["motionDirection"]["closing"] == result[6]
    assert info["motionDirection"]["up"] == result[7]
    assert info["motionDirection"]["down"] == result[8]
    assert info["tilt"] == result[9]
    assert info["timers"] == result[10]


@pytest.mark.asyncio
async def test_get_extended_info_summary_sends_command():
    blind_device = create_device_for_command_testing()
    blind_device._send_command = AsyncMock()
    await blind_device.get_extended_info_summary()
    blind_device._send_command.assert_awaited_once_with(key=COVER_EXT_SUM_KEY)


@pytest.mark.asyncio
@pytest.mark.parametrize("data_value", [(None), (b"\x07"), (b"\x00")])
async def test_get_extended_info_summary_returns_none_when_bad_data(data_value):
    blind_device = create_device_for_command_testing()
    blind_device._send_command = AsyncMock(return_value=data_value)
    assert await blind_device.get_extended_info_summary() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,result", [(bytes([0, 0]), False), (bytes([0, 255]), True)]
)
async def test_get_extended_info_summary(data, result):
    blind_device = create_device_for_command_testing()
    blind_device._send_command = AsyncMock(return_value=data)
    ext_result = await blind_device.get_extended_info_summary()
    assert ext_result["device0"]["light"] == result


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening(reverse_mode):
    """Test passive opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = blind_tilt.SwitchbotBlindTilt(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 10)
    )

    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing(reverse_mode):
    """Test passive closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = blind_tilt.SwitchbotBlindTilt(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening_then_stop(reverse_mode):
    """Test passive stopped after opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = blind_tilt.SwitchbotBlindTilt(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 10)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 10)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing_then_stop(reverse_mode):
    """Test passive stopped after closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = blind_tilt.SwitchbotBlindTilt(
        ble_device, reverse_mode=reverse_mode
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 90)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False
