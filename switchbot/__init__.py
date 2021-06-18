"""Library to handle connection with Switchbot."""
from __future__ import annotations

import binascii
import logging
import threading
import time

import bluepy

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
HANDLE = "cba20002-224d-11e6-9fb8-0002a5d5c51b"

KEY_PASSWORD_PREFIX = "5711"

PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"

OPEN_KEY = "570f450105ff00"  # 570F4501010100
CLOSE_KEY = "570f450105ff64"  # 570F4501010164
POSITION_KEY = "570F450105ff"  # +actual_position ex: 570F450105ff32 for 50%
STOP_KEY = "570F450100ff"

ON_KEY_SUFFIX = "01"
OFF_KEY_SUFFIX = "02"
PRESS_KEY_SUFFIX = "00"

_LOGGER = logging.getLogger(__name__)
CONNECT_LOCK = threading.Lock()


def _process_wohand(data) -> dict:
    """Process woHand/Bot services data."""
    _bot_data = {}

    _sensor_data = binascii.unhexlify(data.encode())

    # 128 switch or 0 press.
    _bot_data["switchMode"] = bool(_sensor_data[1] & 0b10000000)

    # 64 off or 0 for on, if not inversed in app.
    if _bot_data["switchMode"]:
        _bot_data["isOn"] = not bool(_sensor_data[1] & 0b01000000)

    else:
        _bot_data["isOn"] = False

    _bot_data["battery"] = _sensor_data[2] & 0b01111111

    return _bot_data


def _process_wocurtain(data, reverse=True) -> dict:
    """Process woCurtain/Curtain services data."""
    _curtain_data = {}

    _sensor_data = binascii.unhexlify(data.encode())

    _curtain_data["calibration"] = bool(_sensor_data[1] & 0b01000000)
    _curtain_data["battery"] = _sensor_data[2] & 0b01111111
    _position = max(min(_sensor_data[3] & 0b01111111, 100), 0)
    _curtain_data["position"] = (100 - _position) if reverse else _position

    # light sensor level (1-10)
    _curtain_data["lightLevel"] = (_sensor_data[4] >> 4) & 0b00001111

    return _curtain_data


def _process_wosensorth(data) -> dict:
    """Process woSensorTH/Temp sensor services data."""
    _wosensorth_data = {}

    _sensor_data = binascii.unhexlify(data.encode())

    _temp_sign = _sensor_data[4] & 0b10000000
    _temp_c = _temp_sign * ((_sensor_data[4] & 0b01111111) + (_sensor_data[3] / 10))
    _temp_f = (_temp_c * 9 / 5) + 32
    _temp_f = (_temp_f * 10) / 10

    _wosensorth_data["temp"]["c"] = _temp_c
    _wosensorth_data["temp"]["f"] = _temp_f

    _wosensorth_data["fahrenheit"] = bool(_sensor_data[5] & 0b10000000)
    _wosensorth_data["humidity"] = _sensor_data[5] & 0b01111111
    _wosensorth_data["battery"] = _sensor_data[2] & 0b01111111

    return _wosensorth_data


class GetSwitchbotDevices:
    """Scan for all Switchbot devices and return by type."""

    def __init__(self, interface=None) -> None:
        """Get switchbot devices class constructor."""
        self._interface = interface
        self._all_services_data = {}

    def discover(
        self, retry=DEFAULT_RETRY_COUNT, scan_timeout=DEFAULT_SCAN_TIMEOUT
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
                        _model = binascii.unhexlify(value[4:6]).decode()
                        if _model == "H":
                            self._all_services_data[dev_id]["data"] = _process_wohand(
                                value[4:]
                            )
                            self._all_services_data[dev_id]["data"]["rssi"] = dev.rssi
                            self._all_services_data[dev_id]["model"] = _model
                            self._all_services_data[dev_id]["modelName"] = "WoHand"
                        elif _model == "c":
                            self._all_services_data[dev_id][
                                "data"
                            ] = _process_wocurtain(value[4:])
                            self._all_services_data[dev_id]["data"]["rssi"] = dev.rssi
                            self._all_services_data[dev_id]["model"] = _model
                            self._all_services_data[dev_id]["modelName"] = "WoCurtain"
                        elif _model == "T":
                            self._all_services_data[dev_id][
                                "data"
                            ] = _process_wosensorth(value[4:])
                            self._all_services_data[dev_id]["data"]["rssi"] = dev.rssi
                            self._all_services_data[dev_id]["model"] = _model
                            self._all_services_data[dev_id]["modelName"] = "WoSensorTH"

                        else:
                            continue
                    else:
                        self._all_services_data[dev_id][desc] = value

        return self._all_services_data

    def get_curtains(self) -> dict | None:
        """Return all WoCurtain/Curtains devices with services data."""
        if not self._all_services_data:
            self.discover()

        _curtain_devices = {}

        for item in self._all_services_data:
            if self._all_services_data[item]["model"] == "c":
                _curtain_devices[item] = self._all_services_data[item]

        return _curtain_devices

    def get_bots(self) -> dict | None:
        """Return all WoHand/Bot devices with services data."""
        if not self._all_services_data:
            self.discover()

        _bot_devices = {}

        for item in self._all_services_data:
            if self._all_services_data[item]["model"] == "H":
                _bot_devices[item] = self._all_services_data[item]

        return _bot_devices

    def get_device_data(self, mac) -> dict | None:
        """Return data for specific device."""
        if not self._all_services_data:
            self.discover()

        _switchbot_data = {}

        for item in self._all_services_data:
            if self._all_services_data[item]["mac_address"] == mac:
                _switchbot_data = self._all_services_data[item]

        return _switchbot_data


class SwitchbotDevice:
    """Base Representation of a Switchbot Device."""

    def __init__(self, mac, password=None, interface=None, **kwargs) -> None:
        """Switchbot base class constructor."""
        self._interface = interface
        self._mac = mac
        self._device = None
        self._switchbot_device_data = {}
        self._scan_timeout = kwargs.pop("scan_timeout", DEFAULT_SCAN_TIMEOUT)
        self._retry_count = kwargs.pop("retry_count", DEFAULT_RETRY_COUNT)
        if password is None or password == "":
            self._password_encoded = None
        else:
            self._password_encoded = "%x" % (
                binascii.crc32(password.encode("ascii")) & 0xFFFFFFFF
            )

    def _connect(self) -> None:
        if self._device is not None:
            return
        try:
            _LOGGER.debug("Connecting to Switchbot")
            self._device = bluepy.btle.Peripheral(
                self._mac, bluepy.btle.ADDR_TYPE_RANDOM, self._interface
            )
            _LOGGER.debug("Connected to Switchbot")
        except bluepy.btle.BTLEException:
            _LOGGER.debug("Failed connecting to Switchbot", exc_info=True)
            self._device = None
            raise

    def _disconnect(self) -> None:
        if self._device is None:
            return
        _LOGGER.debug("Disconnecting")
        try:
            self._device.disconnect()
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error disconnecting from Switchbot", exc_info=True)
        finally:
            self._device = None

    def _commandkey(self, key) -> str:
        if self._password_encoded is None:
            return key
        key_suffix = PRESS_KEY_SUFFIX
        if key == ON_KEY:
            key_suffix = ON_KEY_SUFFIX
        elif key == OFF_KEY:
            key_suffix = OFF_KEY_SUFFIX
        return KEY_PASSWORD_PREFIX + self._password_encoded + key_suffix

    def _writekey(self, key) -> bool:
        _LOGGER.debug("Prepare to send")
        hand_service = self._device.getServiceByUUID(UUID)
        hand = hand_service.getCharacteristics(HANDLE)[0]
        _LOGGER.debug("Sending command, %s", key)
        write_result = hand.write(binascii.a2b_hex(key), withResponse=True)
        if not write_result:
            _LOGGER.error(
                "Sent command but didn't get a response from Switchbot confirming command was sent."
                " Please check the Switchbot"
            )
        else:
            _LOGGER.info("Successfully sent command to Switchbot (MAC: %s)", self._mac)
        return write_result

    def _sendcommand(self, key, retry) -> bool:
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

    def get_battery_percent(self) -> int:
        """Return device battery level in percent."""
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["battery"]

    def get_device_data(self, retry=DEFAULT_RETRY_COUNT, interface=None) -> dict | None:
        """Find switchbot devices and their advertisement data."""
        if interface:
            _interface = interface
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
                        _model = binascii.unhexlify(value[4:6]).decode()
                        if _model == "H":
                            self._switchbot_device_data["data"] = _process_wohand(
                                value[4:]
                            )
                            self._switchbot_device_data["data"]["rssi"] = dev.rssi
                            self._switchbot_device_data["model"] = _model
                            self._switchbot_device_data["modelName"] = "WoHand"
                        elif _model == "c":
                            self._switchbot_device_data["data"] = _process_wocurtain(
                                value[4:]
                            )
                            self._switchbot_device_data["data"]["rssi"] = dev.rssi
                            self._switchbot_device_data["model"] = _model
                            self._switchbot_device_data["modelName"] = "WoCurtain"
                        elif _model == "T":
                            self._switchbot_device_data["data"] = _process_wosensorth(
                                value[4:]
                            )
                            self._switchbot_device_data["data"]["rssi"] = dev.rssi
                            self._switchbot_device_data["model"] = _model
                            self._switchbot_device_data["modelName"] = "WoSensorTH"

                        else:
                            continue
                    else:
                        self._switchbot_device_data[desc] = value

        return self._switchbot_device_data


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args, **kwargs) -> None:
        """Switchbot Bot/WoHand constructor."""
        super().__init__(*args, **kwargs)
        self._inverse = kwargs.pop("inverse_mode", False)

    def update(self, interface=None) -> None:
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

    def switch_mode(self) -> str:
        """Return true or false from cache."""
        # To get actual position call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["switchMode"]

    def is_on(self) -> bool:
        """Return switch state from cache."""
        # To get actual position call update() first.
        if not self._switchbot_device_data:
            return None

        if self._inverse:
            return not self._switchbot_device_data["data"]["isOn"]

        return self._switchbot_device_data["data"]["isOn"]


class SwitchbotCurtain(SwitchbotDevice):
    """Representation of a Switchbot Curtain."""

    def __init__(self, *args, **kwargs) -> None:
        """Switchbot Curtain/WoCurtain constructor."""

        # The position of the curtain is saved returned with 0 = open and 100 = closed.
        # This is independent of the calibration of the curtain bot (Open left to right/
        # Open right to left/Open from the middle).
        # The parameter 'reverse_mode' reverse these values,
        # if 'reverse_mode' = True, position = 0 equals close
        # and position = 100 equals open. The parameter is default set to True so that
        # the definition of position is the same as in Home Assistant.

        super().__init__(*args, **kwargs)
        self._reverse = kwargs.pop("reverse_mode", True)

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

    def update(self, interface=None) -> None:
        """Update position, battery percent and light level of device."""
        self.get_device_data(retry=self._retry_count, interface=interface)

    def get_position(self) -> int:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["position"]

    def get_light_level(self) -> int:
        """Return cached light level."""
        # To get actual light level call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["lightLevel"]

    def is_reversed(self) -> bool:
        """Return True if the curtain open from left to right."""
        return self._reverse

    def is_calibrated(self) -> bool:
        """Return True curtain is calibrated."""
        # To get actual light level call update() first.
        if not self._switchbot_device_data:
            return None
        return self._switchbot_device_data["data"]["calibration"]
