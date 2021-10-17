"""Library to handle connection with Switchbot."""
from __future__ import annotations
#add extended options
import binascii
import logging
import threading
import time
from typing import Any

import bluepy

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
HANDLE = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
NOTIFICATION_HANDLE = "cba20003-224d-11e6-9fb8-0002a5d5c51b"

KEY_PASSWORD_PREFIX = "5711"
KEY_PASSWORD_NOTIFY_PREFIX = "5712"

PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"

OPEN_KEY = "570f450105ff00"  # 570F4501010100
CLOSE_KEY = "570f450105ff64"  # 570F4501010164
POSITION_KEY = "570F450105ff"  # +actual_position ex: 570F450105ff32 for 50%
STOP_KEY = "570F450100ff"
DEVICE_BASIC_SETTINGS_KEY = "5702"

ON_KEY_SUFFIX = "01"
OFF_KEY_SUFFIX = "02"
PRESS_KEY_SUFFIX = "00"

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


class GetSwitchbotDevices:
    """Scan for all Switchbot devices and return by type."""

    def __init__(self, interface: int | None = None) -> None:
        """Get switchbot devices class constructor."""
        self._interface = interface
        self._all_services_data: dict[str, Any] = {}

    def discover(
        self, retry: int = DEFAULT_RETRY_COUNT, scan_timeout: int = DEFAULT_SCAN_TIMEOUT
    ) -> dict | None:
        """Find switchbot devices and their advertisement data."""

        devices = None

        try:
            devices = bluepy.btle.Scanner(self._interface).scan(scan_timeout)

        except bluepy.btle.BTLEManagementError:
            _LOGGER.error("Error scanning for switchbot devices", exc_info=True)

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Scanning for Switchbot devices failed. Stop trying", exc_info=True
                )
                return None

            _LOGGER.warning(
                "Error scanning for Switchbot devices. Retrying (remaining: %d)",
                retry,
            )
            time.sleep(DEFAULT_RETRY_TIMEOUT)
            return self.discover(retry - 1, scan_timeout)

        for dev in devices:
            if dev.getValueText(7) == UUID:
                dev_id = dev.addr.replace(":", "")
                self._all_services_data[dev_id] = {}
                self._all_services_data[dev_id]["mac_address"] = dev.addr
                for (adtype, desc, value) in dev.getScanData():
                    if adtype == 22:
                        _data = bytes.fromhex(value[4:])
                        _model = chr(_data[0] & 0b01111111)
                        if _model == "H":
                            self._all_services_data[dev_id]["data"] = _process_wohand(
                                _data
                            )
                            self._all_services_data[dev_id]["data"]["rssi"] = dev.rssi
                            self._all_services_data[dev_id]["isEncrypted"] = bool(
                                _data[0] & 0b10000000
                            )
                            self._all_services_data[dev_id]["model"] = _model
                            self._all_services_data[dev_id]["modelName"] = "WoHand"
                        elif _model == "c":
                            self._all_services_data[dev_id][
                                "data"
                            ] = _process_wocurtain(_data)
                            self._all_services_data[dev_id]["data"]["rssi"] = dev.rssi
                            self._all_services_data[dev_id]["isEncrypted"] = bool(
                                _data[0] & 0b10000000
                            )
                            self._all_services_data[dev_id]["model"] = _model
                            self._all_services_data[dev_id]["modelName"] = "WoCurtain"
                        elif _model == "T":
                            self._all_services_data[dev_id][
                                "data"
                            ] = _process_wosensorth(_data)
                            self._all_services_data[dev_id]["data"]["rssi"] = dev.rssi
                            self._all_services_data[dev_id]["isEncrypted"] = bool(
                                _data[0] & 0b10000000
                            )
                            self._all_services_data[dev_id]["model"] = _model
                            self._all_services_data[dev_id]["modelName"] = "WoSensorTH"

                        else:
                            continue
                    else:
                        self._all_services_data[dev_id][desc] = value

        return self._all_services_data

    def get_curtains(self) -> dict:
        """Return all WoCurtain/Curtains devices with services data."""
        if not self._all_services_data:
            self.discover()

        _curtain_devices = {}

        for device, data in self._all_services_data.items():
            if data.get("model") == "c":
                _curtain_devices[device] = data

        return _curtain_devices

    def get_bots(self) -> dict:
        """Return all WoHand/Bot devices with services data."""
        if not self._all_services_data:
            self.discover()

        _bot_devices = {}

        for device, data in self._all_services_data.items():
            if data.get("model") == "H":
                _bot_devices[device] = data

        return _bot_devices

    def get_tempsensors(self) -> dict:
        """Return all WoSensorTH/Temp sensor devices with services data."""
        if not self._all_services_data:
            self.discover()

        _bot_temp = {}

        for device, data in self._all_services_data.items():
            if data.get("model") == "T":
                _bot_temp[device] = data

        return _bot_temp

    def get_device_data(self, mac: str) -> dict:
        """Return data for specific device."""
        if not self._all_services_data:
            self.discover()

        _switchbot_data = {}

        for device in self._all_services_data.values():
            if device["mac_address"] == mac:
                _switchbot_data = device

        return _switchbot_data


class SwitchbotDevice:
    """Base Representation of a Switchbot Device."""

    def __init__(
        self,
        mac: str,
        password: str | None = None,
        interface: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Switchbot base class constructor."""
        self._interface = interface
        self._mac = mac
        self._device = bluepy.btle.Peripheral(
            deviceAddr=None, addrType=bluepy.btle.ADDR_TYPE_RANDOM, iface=interface
        )
        self._switchbot_device_data: dict[str, Any] = {}
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
        key_suffix = PRESS_KEY_SUFFIX
        if key == ON_KEY:
            key_suffix = ON_KEY_SUFFIX
        elif key == OFF_KEY:
            key_suffix = OFF_KEY_SUFFIX
        elif key == DEVICE_BASIC_SETTINGS_KEY:
            return KEY_PASSWORD_NOTIFY_PREFIX + self._password_encoded
        return KEY_PASSWORD_PREFIX + self._password_encoded + key_suffix

    def _writekey(self, key: str) -> Any:
        _LOGGER.debug("Prepare to send")
        hand = self._device.getCharacteristics(uuid=HANDLE)[0]
        _LOGGER.debug("Sending command, %s", key)
        write_result = hand.write(binascii.a2b_hex(key), withResponse=False)
        if not write_result:
            _LOGGER.error(
                "Sent command but didn't get a response from Switchbot confirming command was sent."
                " Please check the Switchbot"
            )
        else:
            _LOGGER.info("Successfully sent command to Switchbot (MAC: %s)", self._mac)
        return write_result

    def _subscribe(self, key: str) -> Any:
        _LOGGER.debug("Subscribe to notifications")
        handle = self._device.getCharacteristics(uuid=NOTIFICATION_HANDLE)[0]
        notify_handle = handle.getHandle() + 1
        response = self._device.writeCharacteristic(
            notify_handle, binascii.a2b_hex(key), withResponse=False
        )
        return response

    def _readkey(self) -> bytes | None:
        _LOGGER.debug("Prepare to read")
        receive_handle = self._device.getCharacteristics(uuid=NOTIFICATION_HANDLE)
        if receive_handle:
            for char in receive_handle:
                read_result: bytes = char.read()
            return read_result
        return None

    def _sendcommand(self, key: str, retry: int) -> bool:
        send_success = False
        command = self._commandkey(key)
        _LOGGER.debug("Sending command to switchbot %s", command)
        with CONNECT_LOCK:
            try:
                self._connect()
                send_success = self._writekey(command)
            except bluepy.btle.BTLEException:
                _LOGGER.warning("Error talking to Switchbot", exc_info=True)
            finally:
                self._disconnect()
        if send_success:
            return True
        if retry < 1:
            _LOGGER.error(
                "Switchbot communication failed. Stopping trying", exc_info=True
            )
            return False
        _LOGGER.warning("Cannot connect to Switchbot. Retrying (remaining: %d)", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._sendcommand(key, retry - 1)

    def get_mac(self) -> str:
        """Return mac address of device."""
        return self._mac

    def get_battery_percent(self) -> Any:
        """Return device battery level in percent."""
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["battery"]

    def get_device_data(
        self, retry: int = DEFAULT_RETRY_COUNT, interface: int | None = None
    ) -> dict | None:
        """Find switchbot devices and their advertisement data."""
        if interface:
            _interface: int | None = interface
        else:
            _interface = self._interface

        devices = None

        try:
            devices = bluepy.btle.Scanner(_interface).scan(self._scan_timeout)

        except bluepy.btle.BTLEManagementError:
            _LOGGER.error("Error scanning for switchbot devices", exc_info=True)

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Scanning for Switchbot devices failed. Stop trying", exc_info=True
                )
                return None

            _LOGGER.warning(
                "Error scanning for Switchbot devices. Retrying (remaining: %d)",
                retry,
            )
            time.sleep(DEFAULT_RETRY_TIMEOUT)
            return self.get_device_data(retry=retry - 1, interface=_interface)

        for dev in devices:
            if self._mac.lower() == dev.addr.lower():
                self._switchbot_device_data["mac_address"] = dev.addr
                for (adtype, desc, value) in dev.getScanData():
                    if adtype == 22:
                        _data = bytes.fromhex(value[4:])
                        _model = chr(_data[0] & 0b01111111)
                        if _model == "H":
                            self._switchbot_device_data["data"] = _process_wohand(_data)
                            self._switchbot_device_data["data"]["rssi"] = dev.rssi
                            self._switchbot_device_data["isEncrypted"] = bool(
                                _data[0] & 0b10000000
                            )
                            self._switchbot_device_data["model"] = _model
                            self._switchbot_device_data["modelName"] = "WoHand"
                        elif _model == "c":
                            self._switchbot_device_data["data"] = _process_wocurtain(
                                _data
                            )
                            self._switchbot_device_data["data"]["rssi"] = dev.rssi
                            self._switchbot_device_data["isEncrypted"] = bool(
                                _data[0] & 0b10000000
                            )
                            self._switchbot_device_data["model"] = _model
                            self._switchbot_device_data["modelName"] = "WoCurtain"
                        elif _model == "T":
                            self._switchbot_device_data["data"] = _process_wosensorth(
                                _data
                            )
                            self._switchbot_device_data["data"]["rssi"] = dev.rssi
                            self._switchbot_device_data["isEncrypted"] = bool(
                                _data[0] & 0b10000000
                            )
                            self._switchbot_device_data["model"] = _model
                            self._switchbot_device_data["modelName"] = "WoSensorTH"

                        else:
                            continue
                    else:
                        self._switchbot_device_data[desc] = value

        return self._switchbot_device_data

    def _get_basic_info(self, retry: int = DEFAULT_RETRY_COUNT) -> bytes:
        """Get device basic settings."""
        send_success = False
        command = self._commandkey(DEVICE_BASIC_SETTINGS_KEY)
        try:
            self._connect()
            self._subscribe(command)
            send_success = self._writekey(command)
            value = self._readkey()
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error talking to Switchbot", exc_info=True)
        finally:
            self._disconnect()

        if send_success and value:

            print("Successfully retrieved data from device " + str(self._mac))

            return value

        if retry < 1:
            _LOGGER.error(
                "Switchbot communication failed. Stopping trying", exc_info=True
            )
            return bytes(0)
        _LOGGER.warning("Cannot connect to Switchbot. Retrying (remaining: %d)", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._get_basic_info(retry - 1)


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Bot/WoHand constructor."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)
        self._settings: dict[str, Any] = {}

    def update(self, interface: int | None = None) -> None:
        """Update mode, battery percent and state of device."""
        self.get_device_data(retry=self._retry_count, interface=interface)

    def turn_on(self) -> bool:
        """Turn device on."""
        return self._sendcommand(ON_KEY, self._retry_count)

    def turn_off(self) -> bool:
        """Turn device off."""
        return self._sendcommand(OFF_KEY, self._retry_count)

    def press(self) -> bool:
        """Press command to device."""
        return self._sendcommand(PRESS_KEY, self._retry_count)

    def get_basic_info(self) -> dict[str, Any]:
        """Get device basic settings."""
        settings_data = self._get_basic_info()
        self._settings["battery"] = settings_data[1]
        self._settings["firmware"] = settings_data[2] / 10.0

        self._settings["timers"] = settings_data[8]
        self._settings["dualStateMode"] = bool(settings_data[9] & 16)
        self._settings["inverseDirection"] = bool(settings_data[9] & 1)
        self._settings["holdSeconds"] = settings_data[10]

        return self._settings

    def switch_mode(self) -> Any:
        """Return true or false from cache."""
        # To get actual position call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["switchMode"]

    def is_on(self) -> Any:
        """Return switch state from cache."""
        # To get actual position call update() first.
        if not self._switchbot_device_data:
            return None

        if self._inverse:
            return not self._switchbot_device_data["data"]["isOn"]

        return self._switchbot_device_data["data"]["isOn"]


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

    def open(self) -> bool:
        """Send open command."""
        return self._sendcommand(OPEN_KEY, self._retry_count)

    def close(self) -> bool:
        """Send close command."""
        return self._sendcommand(CLOSE_KEY, self._retry_count)

    def stop(self) -> bool:
        """Send stop command to device."""
        return self._sendcommand(STOP_KEY, self._retry_count)

    def set_position(self, position: int) -> bool:
        """Send position command (0-100) to device."""
        position = (100 - position) if self._reverse else position
        hex_position = "%0.2X" % position
        return self._sendcommand(POSITION_KEY + hex_position, self._retry_count)

    def update(self, interface: int | None = None) -> None:
        """Update position, battery percent and light level of device."""
        self.get_device_data(retry=self._retry_count, interface=interface)

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["position"]

    def get_basic_info(self) -> dict[str, Any]:
        """Get device basic settings."""
        settings_data = self._get_basic_info()
        self._settings["battery"] = settings_data[1]
        self._settings["firmware"] = settings_data[2] / 10.0

        self._settings["chainLength"] = settings_data[3]

        self._settings["openDirection"] = (
            "right_to_left" if settings_data[4] & 0b10000000 == 128 else "left_to_right"
        )

        self._settings["touchToOpen"] = bool(settings_data[4] & 0b01000000)
        self._settings["light"] = bool(settings_data[4] & 0b00100000)
        self._settings["fault"] = bool(settings_data[4] & 0b00001000)

        self._settings["solarPanel"] = bool(settings_data[5] & 0b00001000)
        self._settings["calibrated"] = bool(settings_data[5] & 0b00000100)
        self._settings["inMotion"] = bool(settings_data[5] & 0b01000011)

        _position = max(min(settings_data[6], 100), 0)
        self._settings["position"] = (100 - _position) if self._reverse else _position

        self._settings["timers"] = settings_data[7]

        return self._settings

    def get_light_level(self) -> Any:
        """Return cached light level."""
        # To get actual light level call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["lightLevel"]

    def is_reversed(self) -> bool:
        """Return True if the curtain open from left to right."""
        return self._reverse

    def is_calibrated(self) -> Any:
        """Return True curtain is calibrated."""
        # To get actual light level call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["calibration"]
