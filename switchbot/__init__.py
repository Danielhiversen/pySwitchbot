"""Library to handle connection with Switchbot."""
from __future__ import annotations

import asyncio
import binascii
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import async_timeout
import bleak
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak_retry_connector import BleakClient, establish_connection

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

# Keys common to all device types
DEVICE_GET_BASIC_SETTINGS_KEY = "5702"
DEVICE_SET_MODE_KEY = "5703"
DEVICE_SET_EXTENDED_KEY = "570f"

# Plug Mini keys
PLUG_ON_KEY = "570f50010180"
PLUG_OFF_KEY = "570f50010100"

# Bot keys
PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"
DOWN_KEY = "570103"
UP_KEY = "570104"

# Curtain keys
OPEN_KEY = "570f450105ff00"  # 570F4501010100
CLOSE_KEY = "570f450105ff64"  # 570F4501010164
POSITION_KEY = "570F450105ff"  # +actual_position ex: 570F450105ff32 for 50%
STOP_KEY = "570F450100ff"
CURTAIN_EXT_SUM_KEY = "570f460401"
CURTAIN_EXT_ADV_KEY = "570f460402"
CURTAIN_EXT_CHAIN_INFO_KEY = "570f468101"

# Base key when encryption is set
KEY_PASSWORD_PREFIX = "571"

_LOGGER = logging.getLogger(__name__)
CONNECT_LOCK = asyncio.Lock()


def _sb_uuid(comms_type: str = "service") -> UUID | str:
    """Return Switchbot UUID."""

    _uuid = {"tx": "002", "rx": "003", "service": "d00"}

    if comms_type in _uuid:
        return UUID(f"cba20{_uuid[comms_type]}-224d-11e6-9fb8-0002a5d5c51b")

    return "Incorrect type, choose between: tx, rx or service"


def _process_wohand(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woHand/Bot services data."""
    _switch_mode = bool(data[1] & 0b10000000)

    _bot_data = {
        "switchMode": _switch_mode,
        "isOn": not bool(data[1] & 0b01000000) if _switch_mode else False,
        "battery": data[2] & 0b01111111,
    }

    return _bot_data


def _process_wocurtain(
    data: bytes, mfr_data: bytes | None, reverse: bool = True
) -> dict[str, bool | int]:
    """Process woCurtain/Curtain services data."""

    _position = max(min(data[3] & 0b01111111, 100), 0)

    _curtain_data = {
        "calibration": bool(data[1] & 0b01000000),
        "battery": data[2] & 0b01111111,
        "inMotion": bool(data[3] & 0b10000000),
        "position": (100 - _position) if reverse else _position,
        "lightLevel": (data[4] >> 4) & 0b00001111,
        "deviceChain": data[4] & 0b00000111,
    }

    return _curtain_data


def _process_wosensorth(data: bytes, mfr_data: bytes | None) -> dict[str, object]:
    """Process woSensorTH/Temp sensor services data."""

    _temp_sign = 1 if data[4] & 0b10000000 else -1
    _temp_c = _temp_sign * ((data[4] & 0b01111111) + ((data[3] & 0b00001111) / 10))
    _temp_f = (_temp_c * 9 / 5) + 32
    _temp_f = (_temp_f * 10) / 10

    _wosensorth_data = {
        "temp": {"c": _temp_c, "f": _temp_f},
        "fahrenheit": bool(data[5] & 0b10000000),
        "humidity": data[5] & 0b01111111,
        "battery": data[2] & 0b01111111,
    }

    return _wosensorth_data


def _process_wocontact(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process woContact Sensor services data."""
    return {
        "tested": bool(data[1] & 0b10000000),
        "motion_detected": bool(data[1] & 0b01000000),
        "battery": data[2] & 0b01111111,
        "contact_open": data[3] & 0b00000010 == 0b00000010,
        "contact_timeout": data[3] & 0b00000110 == 0b00000110,
        "is_light": bool(data[3] & 0b00000001),
        "button_count": (data[7] & 0b11110000) >> 4,
    }


def _process_wopresence(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process WoPresence Sensor services data."""
    return {
        "tested": bool(data[1] & 0b10000000),
        "motion_detected": bool(data[1] & 0b01000000),
        "battery": data[2] & 0b01111111,
        "led": (data[5] & 0b00100000) >> 5,
        "iot": (data[5] & 0b00010000) >> 4,
        "sense_distance": (data[5] & 0b00001100) >> 2,
        "light_intensity": data[5] & 0b00000011,
        "is_light": bool(data[5] & 0b00000010),
    }


def _process_woplugmini(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process plug mini."""
    return {
        "switchMode": True,
        "isOn": mfr_data[7] == 0x80,
        "wifi_rssi": -mfr_data[9],
    }


def _process_color_bulb(data: bytes, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process WoBulb services data."""
    return {
        "sequence_number": mfr_data[6],
        "isOn": bool(mfr_data[7] & 0b10000000),
        "brightness": mfr_data[7] & 0b01111111,
        "delay": bool(mfr_data[8] & 0b10000000),
        "preset": bool(mfr_data[8] & 0b00001000),
        "light_state": mfr_data[8] & 0b00000111,
        "speed": mfr_data[9] & 0b01111111,
        "loop_index": mfr_data[10] & 0b11111110,
    }


@dataclass
class SwitchBotAdvertisement:
    """Switchbot advertisement."""

    address: str
    data: dict[str, Any]
    device: BLEDevice


def parse_advertisement_data(
    device: BLEDevice, advertisement_data: AdvertisementData
) -> SwitchBotAdvertisement | None:
    """Parse advertisement data."""
    _services = list(advertisement_data.service_data.values())
    _mgr_datas = list(advertisement_data.manufacturer_data.values())

    if not _services:
        return
    _service_data = _services[0]
    _mfr_data = _mgr_datas[0] if _mgr_datas else None
    _model = chr(_service_data[0] & 0b01111111)

    supported_types: dict[str, dict[str, Any]] = {
        "d": {"modelName": "WoContact", "func": _process_wocontact},
        "H": {"modelName": "WoHand", "func": _process_wohand},
        "s": {"modelName": "WoPresence", "func": _process_wopresence},
        "c": {"modelName": "WoCurtain", "func": _process_wocurtain},
        "T": {"modelName": "WoSensorTH", "func": _process_wosensorth},
        "i": {"modelName": "WoSensorTH", "func": _process_wosensorth},
        "g": {"modelName": "WoPlug", "func": _process_woplugmini},
        "u": {"modelName": "WoBulb", "func": _process_color_bulb},
    }

    data = {
        "address": device.address,  # MacOS uses UUIDs
        "rawAdvData": list(advertisement_data.service_data.values())[0],
        "data": {
            "rssi": device.rssi,
        },
    }

    if _model in supported_types:

        data.update(
            {
                "isEncrypted": bool(_service_data[0] & 0b10000000),
                "model": _model,
                "modelName": supported_types[_model]["modelName"],
                "data": supported_types[_model]["func"](_service_data, _mfr_data),
            }
        )

        data["data"]["rssi"] = device.rssi

    return SwitchBotAdvertisement(device.address, data, device)


class GetSwitchbotDevices:
    """Scan for all Switchbot devices and return by type."""

    def __init__(self, interface: int = 0) -> None:
        """Get switchbot devices class constructor."""
        self._interface = f"hci{interface}"
        self._adv_data: dict[str, SwitchBotAdvertisement] = {}

    def detection_callback(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> None:
        discovery = parse_advertisement_data(device, advertisement_data)
        if discovery:
            self._adv_data[discovery.address] = discovery

    async def discover(
        self, retry: int = DEFAULT_RETRY_COUNT, scan_timeout: int = DEFAULT_SCAN_TIMEOUT
    ) -> dict:
        """Find switchbot devices and their advertisement data."""

        devices = None
        devices = bleak.BleakScanner(
            # TODO: Find new UUIDs to filter on. For example, see
            # https://github.com/OpenWonderLabs/SwitchBotAPI-BLE/blob/4ad138bb09f0fbbfa41b152ca327a78c1d0b6ba9/devicetypes/meter.md
            adapter=self._interface,
        )
        devices.register_detection_callback(self.detection_callback)

        async with CONNECT_LOCK:
            await devices.start()
            await asyncio.sleep(scan_timeout)
            await devices.stop()

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Scanning for Switchbot devices failed. Stop trying", exc_info=True
                )
                return self._adv_data

            _LOGGER.warning(
                "Error scanning for Switchbot devices. Retrying (remaining: %d)",
                retry,
            )
            await asyncio.sleep(DEFAULT_RETRY_TIMEOUT)
            return await self.discover(retry - 1, scan_timeout)

        return self._adv_data

    async def _get_devices_by_model(
        self,
        model: str,
    ) -> dict:
        """Get switchbot devices by type."""
        if not self._adv_data:
            await self.discover()

        return {
            address: adv
            for address, adv in self._adv_data.items()
            if adv.data.get("model") == model
        }

    async def get_curtains(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoCurtain/Curtains devices with services data."""
        return await self._get_devices_by_model("c")

    async def get_bots(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoHand/Bot devices with services data."""
        return await self._get_devices_by_model("H")

    async def get_tempsensors(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoSensorTH/Temp sensor devices with services data."""
        base_meters = await self._get_devices_by_model("T")
        plus_meters = await self._get_devices_by_model("i")
        return {**base_meters, **plus_meters}

    async def get_contactsensors(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoContact/Contact sensor devices with services data."""
        return await self._get_devices_by_model("d")

    async def get_device_data(
        self, address: str
    ) -> dict[str, SwitchBotAdvertisement] | None:
        """Return data for specific device."""
        if not self._adv_data:
            await self.discover()

        _switchbot_data = {
            device: data
            for device, data in self._adv_data.items()
            # MacOS uses UUIDs instead of MAC addresses
            if data.get("address") == address
        }

        return _switchbot_data


class SwitchbotDevice:
    """Base Representation of a Switchbot Device."""

    def __init__(
        self,
        device: BLEDevice,
        password: str | None = None,
        interface: int = 0,
        **kwargs: Any,
    ) -> None:
        """Switchbot base class constructor."""
        self._interface = f"hci{interface}"
        self._device = device
        self._sb_adv_data: SwitchBotAdvertisement | None = None
        self._scan_timeout: int = kwargs.pop("scan_timeout", DEFAULT_SCAN_TIMEOUT)
        self._retry_count: int = kwargs.pop("retry_count", DEFAULT_RETRY_COUNT)
        if password is None or password == "":
            self._password_encoded = None
        else:
            self._password_encoded = "%x" % (
                binascii.crc32(password.encode("ascii")) & 0xFFFFFFFF
            )

    def _commandkey(self, key: str) -> str:
        """Add password to key if set."""
        if self._password_encoded is None:
            return key
        key_action = key[3]
        key_suffix = key[4:]
        return KEY_PASSWORD_PREFIX + key_action + self._password_encoded + key_suffix

    async def _sendcommand(self, key: str, retry: int) -> bytes:
        """Send command to device and read response."""
        command = bytearray.fromhex(self._commandkey(key))
        _LOGGER.debug("Sending command to switchbot %s", command)
        max_attempts = retry + 1
        async with CONNECT_LOCK:
            for attempt in range(max_attempts):
                try:
                    return await self._send_command_locked(key, command)
                except (bleak.BleakError, asyncio.exceptions.TimeoutError):
                    if attempt == retry:
                        _LOGGER.error(
                            "Switchbot communication failed. Stopping trying",
                            exc_info=True,
                        )
                        return b"\x00"

                    _LOGGER.debug("Switchbot communication failed with:", exc_info=True)

        raise RuntimeError("Unreachable")

    @property
    def name(self) -> str:
        """Return device name."""
        return f"{self._device.name} ({self._device.address})"

    async def _send_command_locked(self, key: str, command: bytes) -> bytes:
        """Send command to device and read response."""
        client: BleakClient | None = None
        try:
            _LOGGER.debug("%s: Connnecting to switchbot", self.name)
            client = await establish_connection(
                BleakClient, self._device, self.name, max_attempts=1
            )
            _LOGGER.debug(
                "%s: Connnected to switchbot: %s", self.name, client.is_connected
            )
            future: asyncio.Future[bytearray] = asyncio.Future()

            def _notification_handler(sender: int, data: bytearray) -> None:
                """Handle notification responses."""
                if future.done():
                    _LOGGER.debug("%s: Notification handler already done", self.name)
                    return
                future.set_result(data)

            _LOGGER.debug("%s: Subscribe to notifications", self.name)
            await client.start_notify(_sb_uuid(comms_type="rx"), _notification_handler)

            _LOGGER.debug("%s: Sending command, %s", self.name, key)
            await client.write_gatt_char(_sb_uuid(comms_type="tx"), command, False)

            async with async_timeout.timeout(5):
                notify_msg = await future
            _LOGGER.info("%s: Notification received: %s", self.name, notify_msg)

            _LOGGER.debug("%s: UnSubscribe to notifications", self.name)
            await client.stop_notify(_sb_uuid(comms_type="rx"))

        finally:
            if client:
                await client.disconnect()

        if notify_msg == b"\x07":
            _LOGGER.error("Password required")
        elif notify_msg == b"\t":
            _LOGGER.error("Password incorrect")
        return notify_msg

    def get_address(self) -> str:
        """Return address of device."""
        return self._device.address

    def _get_adv_value(self, key: str) -> Any:
        """Return value from advertisement data."""
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data.data["data"][key]

    def get_battery_percent(self) -> Any:
        """Return device battery level in percent."""
        return self._get_adv_value("battery")

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        self._sb_adv_data = advertisement
        self._device = advertisement.device

    async def get_device_data(
        self, retry: int = DEFAULT_RETRY_COUNT, interface: int | None = None
    ) -> dict | None:
        """Find switchbot devices and their advertisement data."""
        if interface:
            _interface: int = interface
        else:
            _interface = int(self._interface.replace("hci", ""))

        _data = await GetSwitchbotDevices(interface=_interface).discover(
            retry=retry, scan_timeout=self._scan_timeout
        )

        if self._device.address in _data:
            self._sb_adv_data = _data[self._device.address]

        return self._sb_adv_data


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Bot/WoHand constructor."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)
        self._settings: dict[str, Any] = {}

    async def update(self, interface: int | None = None) -> None:
        """Update mode, battery percent and state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._sendcommand(ON_KEY, self._retry_count)

        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode and doesn't have on state")
            return True

        return False

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._sendcommand(OFF_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode and doesn't have off state")
            return True

        return False

    async def hand_up(self) -> bool:
        """Raise device arm."""
        result = await self._sendcommand(UP_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode")
            return True

        return False

    async def hand_down(self) -> bool:
        """Lower device arm."""
        result = await self._sendcommand(DOWN_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode")
            return True

        return False

    async def press(self) -> bool:
        """Press command to device."""
        result = await self._sendcommand(PRESS_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in switch mode")
            return True

        return False

    async def set_switch_mode(
        self, switch_mode: bool = False, strength: int = 100, inverse: bool = False
    ) -> bool:
        """Change bot mode."""
        mode_key = format(switch_mode, "b") + format(inverse, "b")
        strength_key = f"{strength:0{2}x}"  # to hex with padding to double digit

        result = await self._sendcommand(
            DEVICE_SET_MODE_KEY + strength_key + mode_key, self._retry_count
        )

        if result[0] == 1:
            return True

        return False

    async def set_long_press(self, duration: int = 0) -> bool:
        """Set bot long press duration."""
        duration_key = f"{duration:0{2}x}"  # to hex with padding to double digit

        result = await self._sendcommand(
            DEVICE_SET_EXTENDED_KEY + "08" + duration_key, self._retry_count
        )

        if result[0] == 1:
            return True

        return False

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        _data = await self._sendcommand(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessfull, please try again")
            return None

        self._settings = {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "strength": _data[3],
            "timers": _data[8],
            "switchMode": bool(_data[9] & 16),
            "inverseDirection": bool(_data[9] & 1),
            "holdSeconds": _data[10],
        }

        return self._settings

    def switch_mode(self) -> Any:
        """Return true or false from cache."""
        # To get actual position call update() first.
        return self._get_adv_value("switchMode")

    def is_on(self) -> Any:
        """Return switch state from cache."""
        # To get actual position call update() first.
        value = self._get_adv_value("isOn")
        if value is None:
            return None

        if self._inverse:
            return not value
        return value


class SwitchbotCurtain(SwitchbotDevice):
    """Representation of a Switchbot Curtain."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Curtain/WoCurtain constructor."""

        # The position of the curtain is saved returned with 0 = open and 100 = closed.
        # This is independent of the calibration of the curtain bot (Open left to right/
        # Open right to left/Open from the middle).
        # The parameter 'reverse_mode' reverse these values,
        # if 'reverse_mode' = True, position = 0 equals close
        # and position = 100 equals open. The parameter is default set to True so that
        # the definition of position is the same as in Home Assistant.

        super().__init__(*args, **kwargs)
        self._reverse: bool = kwargs.pop("reverse_mode", True)
        self._settings: dict[str, Any] = {}
        self.ext_info_sum: dict[str, Any] = {}
        self.ext_info_adv: dict[str, Any] = {}

    async def open(self) -> bool:
        """Send open command."""
        result = await self._sendcommand(OPEN_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def close(self) -> bool:
        """Send close command."""
        result = await self._sendcommand(CLOSE_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def stop(self) -> bool:
        """Send stop command to device."""
        result = await self._sendcommand(STOP_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def set_position(self, position: int) -> bool:
        """Send position command (0-100) to device."""
        position = (100 - position) if self._reverse else position
        hex_position = "%0.2X" % position
        result = await self._sendcommand(POSITION_KEY + hex_position, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def update(self, interface: int | None = None) -> None:
        """Update position, battery percent and light level of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        return self._get_adv_value("position")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        _data = await self._sendcommand(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessfull, please try again")
            return None

        _position = max(min(_data[6], 100), 0)

        self._settings = {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "chainLength": _data[3],
            "openDirection": (
                "right_to_left" if _data[4] & 0b10000000 == 128 else "left_to_right"
            ),
            "touchToOpen": bool(_data[4] & 0b01000000),
            "light": bool(_data[4] & 0b00100000),
            "fault": bool(_data[4] & 0b00001000),
            "solarPanel": bool(_data[5] & 0b00001000),
            "calibrated": bool(_data[5] & 0b00000100),
            "inMotion": bool(_data[5] & 0b01000011),
            "position": (100 - _position) if self._reverse else _position,
            "timers": _data[7],
        }

        return self._settings

    async def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get basic info for all devices in chain."""
        _data = await self._sendcommand(
            key=CURTAIN_EXT_SUM_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessfull, please try again")
            return None

        self.ext_info_sum["device0"] = {
            "openDirectionDefault": not bool(_data[1] & 0b10000000),
            "touchToOpen": bool(_data[1] & 0b01000000),
            "light": bool(_data[1] & 0b00100000),
            "openDirection": (
                "left_to_right" if _data[1] & 0b00010000 == 1 else "right_to_left"
            ),
        }

        # if grouped curtain device present.
        if _data[2] != 0:
            self.ext_info_sum["device1"] = {
                "openDirectionDefault": not bool(_data[1] & 0b10000000),
                "touchToOpen": bool(_data[1] & 0b01000000),
                "light": bool(_data[1] & 0b00100000),
                "openDirection": (
                    "left_to_right" if _data[1] & 0b00010000 else "right_to_left"
                ),
            }

        return self.ext_info_sum

    async def get_extended_info_adv(self) -> dict[str, Any] | None:
        """Get advance page info for device chain."""

        _data = await self._sendcommand(
            key=CURTAIN_EXT_ADV_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessfull, please try again")
            return None

        _state_of_charge = [
            "not_charging",
            "charging_by_adapter",
            "charging_by_solar",
            "fully_charged",
            "solar_not_charging",
            "charging_error",
        ]

        self.ext_info_adv["device0"] = {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "stateOfCharge": _state_of_charge[_data[3]],
        }

        # If grouped curtain device present.
        if _data[4]:
            self.ext_info_adv["device1"] = {
                "battery": _data[4],
                "firmware": _data[5] / 10.0,
                "stateOfCharge": _state_of_charge[_data[6]],
            }

        return self.ext_info_adv

    def get_light_level(self) -> Any:
        """Return cached light level."""
        # To get actual light level call update() first.
        return self._get_adv_value("lightLevel")

    def is_reversed(self) -> bool:
        """Return True if curtain position is opposite from SB data."""
        return self._reverse

    def is_calibrated(self) -> Any:
        """Return True curtain is calibrated."""
        # To get actual light level call update() first.
        return self._get_adv_value("calibration")


class SwitchbotPlugMini(SwitchbotDevice):
    """Representation of a Switchbot plug mini."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot plug mini constructor."""
        super().__init__(*args, **kwargs)
        self._settings: dict[str, Any] = {}

    async def update(self, interface: int | None = None) -> None:
        """Update state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._sendcommand(PLUG_ON_KEY, self._retry_count)
        return result[1] == 0x80

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._sendcommand(PLUG_OFF_KEY, self._retry_count)
        return result[1] == 0x00

    def is_on(self) -> Any:
        """Return switch state from cache."""
        # To get actual position call update() first.
        value = self._get_adv_value("isOn")
        if value is None:
            return None
        return value
