"""Library to handle connection with Switchbot."""
from __future__ import annotations

import binascii
import logging
import threading
import time
from typing import Any

import bluepy

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

# Switchbot device BTLE handles
UUID = bluepy.btle.UUID("cba20d00-224d-11e6-9fb8-0002a5d5c51b")
HANDLE = bluepy.btle.UUID("cba20002-224d-11e6-9fb8-0002a5d5c51b")
NOTIFICATION_HANDLE = bluepy.btle.UUID("cba20003-224d-11e6-9fb8-0002a5d5c51b")

# Keys common to all device types
DEVICE_GET_BASIC_SETTINGS_KEY = "5702"
DEVICE_SET_MODE_KEY = "5703"
DEVICE_SET_EXTENDED_KEY = "570f"

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

# Keys used when encryption is set
KEY_PASSWORD_PREFIX = "571"

_LOGGER = logging.getLogger(__name__)
CONNECT_LOCK = threading.Lock()


def _process_wohand(data: bytes) -> dict[str, bool | int]:
    """Process woHand/Bot services data."""
    _bot_data: dict[str, bool | int] = {}

    # 128 switch or 0 press.
    _bot_data["switchMode"] = bool(data[1] & 0b10000000)

    # 64 off or 0 for on, if not inversed in app.
    if _bot_data["switchMode"]:
        _bot_data["isOn"] = not bool(data[1] & 0b01000000)

    else:
        _bot_data["isOn"] = False

    _bot_data["battery"] = data[2] & 0b01111111

    return _bot_data


def _process_wocurtain(data: bytes, reverse: bool = True) -> dict[str, bool | int]:
    """Process woCurtain/Curtain services data."""
    _curtain_data: dict[str, bool | int] = {}

    _curtain_data["calibration"] = bool(data[1] & 0b01000000)
    _curtain_data["battery"] = data[2] & 0b01111111
    _curtain_data["inMotion"] = bool(data[3] & 0b10000000)
    _position = max(min(data[3] & 0b01111111, 100), 0)
    _curtain_data["position"] = (100 - _position) if reverse else _position

    # light sensor level (1-10)
    _curtain_data["lightLevel"] = (data[4] >> 4) & 0b00001111
    _curtain_data["deviceChain"] = data[4] & 0b00000111

    return _curtain_data


def _process_wosensorth(data: bytes) -> dict[str, Any]:
    """Process woSensorTH/Temp sensor services data."""
    _wosensorth_data: dict[str, Any] = {}

    _temp_sign = 1 if data[4] & 0b10000000 else -1
    _temp_c = _temp_sign * ((data[4] & 0b01111111) + (data[3] / 10))
    _temp_f = (_temp_c * 9 / 5) + 32
    _temp_f = (_temp_f * 10) / 10

    _wosensorth_data["temp"] = {}
    _wosensorth_data["temp"]["c"] = _temp_c
    _wosensorth_data["temp"]["f"] = _temp_f

    _wosensorth_data["fahrenheit"] = bool(data[5] & 0b10000000)
    _wosensorth_data["humidity"] = data[5] & 0b01111111
    _wosensorth_data["battery"] = data[2] & 0b01111111

    return _wosensorth_data


def _btle_scan(
    retry: int = DEFAULT_RETRY_COUNT,
    interface: int = 0,
    passive: bool = False,
    scan_timeout: int = 5,
    mac: str | None = None,
) -> dict[str, Any]:
    """Scan for bluetooth le adv data."""
    devices = None
    _data: dict[str, Any] = {}

    with CONNECT_LOCK:
        try:
            devices = bluepy.btle.Scanner(interface).scan(scan_timeout, passive)
        except bluepy.btle.BTLEManagementError:
            _LOGGER.error("Error scanning for switchbot devices", exc_info=True)

    if devices is None:
        if retry < 1:
            _LOGGER.error(
                "Scanning for Switchbot devices failed. Stop trying", exc_info=True
            )
            return _data

        _LOGGER.warning(
            "Error scanning for Switchbot devices. Retrying (remaining: %d)",
            retry,
        )
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return _btle_scan(
            retry=retry - 1,
            interface=interface,
            passive=passive,
            scan_timeout=scan_timeout,
            mac=mac,
        )

    for dev in devices:
        if dev.getValueText(7) == UUID:
            if mac:
                if dev.addr.lower() == mac.lower():
                    _data = _process_btle_adv_data(dev)
            else:
                dev_id = dev.addr.replace(":", "")
                _data[dev_id] = _process_btle_adv_data(dev)

    return _data


def _process_btle_adv_data(dev: bluepy.btle.ScanEntry) -> dict[str, Any]:
    """Process bt le adv data."""
    _adv_data: dict[str, Any] = {}

    _adv_data = {"mac_address": dev.addr}
    for (adtype, desc, value) in dev.getScanData():
        if adtype == 22:
            _data = bytes.fromhex(value[4:])
            _model = chr(_data[0] & 0b01111111)
            _adv_data["isEncrypted"] = bool(_data[0] & 0b10000000)
            _adv_data["model"] = _model
            if _model == "H":
                _adv_data["data"] = _process_wohand(_data)
                _adv_data["data"]["rssi"] = dev.rssi
                _adv_data["modelName"] = "WoHand"
            elif _model == "c":
                _adv_data["data"] = _process_wocurtain(_data)
                _adv_data["data"]["rssi"] = dev.rssi
                _adv_data["modelName"] = "WoCurtain"
            elif _model == "T":
                _adv_data["data"] = _process_wosensorth(_data)
                _adv_data["data"]["rssi"] = dev.rssi
                _adv_data["modelName"] = "WoSensorTH"

            else:
                continue
        else:
            _adv_data[desc] = value

    return _adv_data


class GetSwitchbotDevices:
    """Scan for all Switchbot devices and return by type."""

    def __init__(self, interface: int = 0) -> None:
        """Get switchbot devices class constructor."""
        self._interface = interface
        self._adv_data: dict[str, Any] = {}

    def discover(
        self,
        retry: int = DEFAULT_RETRY_COUNT,
        scan_timeout: int = DEFAULT_SCAN_TIMEOUT,
        passive: bool = False,
    ) -> dict[str, Any] | None:
        """Find switchbot devices and their advertisement data."""
        self._adv_data = _btle_scan(
            retry=retry,
            interface=self._interface,
            passive=passive,
            scan_timeout=scan_timeout,
        )

        return self._adv_data

    def get_curtains(self) -> dict:
        """Return all WoCurtain/Curtains devices with services data."""
        if not self._adv_data:
            self.discover()

        _curtain_devices = {
            device: data
            for device, data in self._adv_data.items()
            if data.get("model") == "c"
        }

        return _curtain_devices

    def get_bots(self) -> dict:
        """Return all WoHand/Bot devices with services data."""
        if not self._adv_data:
            self.discover()

        _bot_devices = {
            device: data
            for device, data in self._adv_data.items()
            if data.get("model") == "H"
        }

        return _bot_devices

    def get_tempsensors(self) -> dict:
        """Return all WoSensorTH/Temp sensor devices with services data."""
        if not self._adv_data:
            self.discover()

        _bot_temp = {
            device: data
            for device, data in self._adv_data.items()
            if data.get("model") == "T"
        }

        return _bot_temp

    def get_device_data(self, mac: str) -> dict:
        """Return data for specific device."""
        if not self._adv_data:
            self.discover()

        _switchbot_data = {
            device: data
            for device, data in self._adv_data.items()
            if data.get("mac_address") == mac
        }

        return _switchbot_data


class SwitchbotDevice:
    """Base Representation of a Switchbot Device."""

    def __init__(
        self,
        mac: str,
        password: str | None = None,
        interface: int = 0,
        **kwargs: Any,
    ) -> None:
        """Switchbot base class constructor."""
        self._interface = interface
        self._mac = mac
        self._device = bluepy.btle.Peripheral(
            deviceAddr=None, addrType=bluepy.btle.ADDR_TYPE_RANDOM, iface=interface
        )
        self._sb_adv_data: dict[str, Any] = {}
        self._scan_timeout: int = kwargs.pop("scan_timeout", DEFAULT_SCAN_TIMEOUT)
        self._retry_count: int = kwargs.pop("retry_count", DEFAULT_RETRY_COUNT)
        if password is None or password == "":
            self._password_encoded = None
        else:
            self._password_encoded = "%x" % (
                binascii.crc32(password.encode("ascii")) & 0xFFFFFFFF
            )

    def _connect(self) -> None:
        try:
            _LOGGER.debug("Connecting to Switchbot")
            self._device.connect(
                self._mac, bluepy.btle.ADDR_TYPE_RANDOM, self._interface
            )
            _LOGGER.debug("Connected to Switchbot")
        except bluepy.btle.BTLEException:
            _LOGGER.debug("Failed connecting to Switchbot", exc_info=True)
            raise

    def _disconnect(self) -> None:
        _LOGGER.debug("Disconnecting")
        try:
            self._device.disconnect()
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error disconnecting from Switchbot", exc_info=True)

    def _commandkey(self, key: str) -> str:
        if self._password_encoded is None:
            return key
        key_action = key[3]
        key_suffix = key[4:]
        return KEY_PASSWORD_PREFIX + key_action + self._password_encoded + key_suffix

    def _writekey(self, key: str) -> Any:
        _LOGGER.debug("Prepare to send")
        hand = self._device.getCharacteristics(uuid=HANDLE)[0]
        _LOGGER.debug("Sending command, %s", key)
        write_result = hand.write(bytes.fromhex(key), withResponse=False)
        if not write_result:
            _LOGGER.error(
                "Sent command but didn't get a response from Switchbot confirming command was sent."
                " Please check the Switchbot"
            )
        else:
            _LOGGER.info("Successfully sent command to Switchbot (MAC: %s)", self._mac)
        return write_result

    def _subscribe(self) -> None:
        _LOGGER.debug("Subscribe to notifications")
        enable_notify_flag = b"\x01\x00"  # standard gatt flag to enable notification
        handle = self._device.getCharacteristics(uuid=NOTIFICATION_HANDLE)[0]
        notify_handle = handle.getHandle() + 1
        self._device.writeCharacteristic(
            notify_handle, enable_notify_flag, withResponse=False
        )

    def _readkey(self) -> bytes:
        _LOGGER.debug("Prepare to read")
        receive_handle = self._device.getCharacteristics(uuid=NOTIFICATION_HANDLE)
        if receive_handle:
            for char in receive_handle:
                read_result: bytes = char.read()
            return read_result
        return b"\x00"

    def _sendcommand(self, key: str, retry: int) -> bytes:
        send_success = False
        command = self._commandkey(key)
        notify_msg = b"\x00"
        _LOGGER.debug("Sending command to switchbot %s", command)
        with CONNECT_LOCK:
            try:
                self._connect()
                self._subscribe()
                send_success = self._writekey(command)
                notify_msg = self._readkey()
            except bluepy.btle.BTLEException:
                _LOGGER.warning("Error talking to Switchbot", exc_info=True)
            finally:
                self._disconnect()
        if send_success:
            if notify_msg == b"\x07":
                _LOGGER.error("Password required")
            elif notify_msg == b"\t":
                _LOGGER.error("Password incorrect")

            return notify_msg
        if retry < 1:
            _LOGGER.error(
                "Switchbot communication failed. Stopping trying", exc_info=True
            )
            return notify_msg
        _LOGGER.warning("Cannot connect to Switchbot. Retrying (remaining: %d)", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._sendcommand(key, retry - 1)

    def get_mac(self) -> str:
        """Return mac address of device."""
        return self._mac

    def get_battery_percent(self) -> Any:
        """Return device battery level in percent."""
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data["data"]["battery"]

    def get_device_data(
        self,
        retry: int = DEFAULT_RETRY_COUNT,
        interface: int | None = None,
        passive: bool = False,
    ) -> dict | None:
        """Find switchbot devices and their advertisement data."""
        if interface:
            _interface: int = interface
        else:
            _interface = self._interface

        self._sb_adv_data = _btle_scan(
            retry=retry,
            interface=_interface,
            passive=passive,
            scan_timeout=self._scan_timeout,
            mac=self._mac,
        )

        return self._sb_adv_data


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Bot/WoHand constructor."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)
        self._settings: dict[str, Any] = {}

    def update(self, interface: int | None = None, passive: bool = False) -> None:
        """Update mode, battery percent and state of device."""
        self.get_device_data(
            retry=self._retry_count, interface=interface, passive=passive
        )

    def turn_on(self) -> bool:
        """Turn device on."""
        result = self._sendcommand(ON_KEY, self._retry_count)

        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode and doesn't have on state")
            return True

        return False

    def turn_off(self) -> bool:
        """Turn device off."""
        result = self._sendcommand(OFF_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode and doesn't have off state")
            return True

        return False

    def hand_up(self) -> bool:
        """Raise device arm."""
        result = self._sendcommand(UP_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode")
            return True

        return False

    def hand_down(self) -> bool:
        """Lower device arm."""
        result = self._sendcommand(DOWN_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in press mode")
            return True

        return False

    def press(self) -> bool:
        """Press command to device."""
        result = self._sendcommand(PRESS_KEY, self._retry_count)
        if result[0] == 1:
            return True

        if result[0] == 5:
            _LOGGER.debug("Bot is in switch mode")
            return True

        return False

    def set_switch_mode(
        self, switch_mode: bool = False, strength: int = 100, inverse: bool = False
    ) -> bool:
        """Change bot mode."""
        mode_key = format(switch_mode, "b") + format(inverse, "b")
        strength_key = f"{strength:0{2}x}"  # to hex with padding to double digit

        result = self._sendcommand(
            DEVICE_SET_MODE_KEY + strength_key + mode_key, self._retry_count
        )

        if result[0] == 1:
            return True

        return False

    def set_long_press(self, duration: int = 0) -> bool:
        """Set bot long press duration."""
        duration_key = f"{duration:0{2}x}"  # to hex with padding to double digit

        result = self._sendcommand(
            DEVICE_SET_EXTENDED_KEY + "08" + duration_key, self._retry_count
        )

        if result[0] == 1:
            return True

        return False

    def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        _data = self._sendcommand(
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
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data["data"]["switchMode"]

    def is_on(self) -> Any:
        """Return switch state from cache."""
        # To get actual position call update() first.
        if not self._sb_adv_data:
            return None

        if self._inverse:
            return not self._sb_adv_data["data"]["isOn"]

        return self._sb_adv_data["data"]["isOn"]


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

    def open(self) -> bool:
        """Send open command."""
        result = self._sendcommand(OPEN_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    def close(self) -> bool:
        """Send close command."""
        result = self._sendcommand(CLOSE_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    def stop(self) -> bool:
        """Send stop command to device."""
        result = self._sendcommand(STOP_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    def set_position(self, position: int) -> bool:
        """Send position command (0-100) to device."""
        position = (100 - position) if self._reverse else position
        hex_position = "%0.2X" % position
        result = self._sendcommand(POSITION_KEY + hex_position, self._retry_count)
        if result[0] == 1:
            return True

        return False

    def update(self, interface: int | None = None, passive: bool = False) -> None:
        """Update position, battery percent and light level of device."""
        self.get_device_data(
            retry=self._retry_count, interface=interface, passive=passive
        )

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data["data"]["position"]

    def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        _data = self._sendcommand(
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

    def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get basic info for all devices in chain."""
        _data = self._sendcommand(key=CURTAIN_EXT_SUM_KEY, retry=self._retry_count)

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

    def get_extended_info_adv(self) -> dict[str, Any] | None:
        """Get advance page info for device chain."""
        _data = self._sendcommand(key=CURTAIN_EXT_ADV_KEY, retry=self._retry_count)

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
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data["data"]["lightLevel"]

    def is_reversed(self) -> bool:
        """Return True if curtain position is opposite from SB data."""
        return self._reverse

    def is_calibrated(self) -> Any:
        """Return True curtain is calibrated."""
        # To get actual light level call update() first.
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data["data"]["calibration"]
