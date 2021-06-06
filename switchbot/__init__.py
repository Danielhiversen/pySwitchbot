"""Library to handle connection with Switchbot"""
import binascii
import logging
import time

import bluepy

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 0.2
DEFAULT_TIME_BETWEEN_UPDATE_COMMAND = 10

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


class SwitchbotDevice:
    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes
    """Base Representation of a Switchbot Device."""

    def __init__(self, mac, password=None, interface=None, **kwargs) -> None:
        self._interface = interface
        self._mac = mac
        self._device = None
        self._battery_percent = 0
        self._retry_count = kwargs.pop("retry_count", DEFAULT_RETRY_COUNT)
        self._time_between_update_command = kwargs.pop(
            "time_between_update_command", DEFAULT_TIME_BETWEEN_UPDATE_COMMAND
        )
        self._last_time_command_send = time.time()
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
            _LOGGER.debug("Connecting to Switchbot...")
            self._device = bluepy.btle.Peripheral(
                self._mac, bluepy.btle.ADDR_TYPE_RANDOM, self._interface
            )
            _LOGGER.debug("Connected to Switchbot.")
        except bluepy.btle.BTLEException:
            _LOGGER.debug("Failed connecting to Switchbot.", exc_info=True)
            self._device = None
            raise

    def _disconnect(self) -> None:
        if self._device is None:
            return
        _LOGGER.debug("Disconnecting")
        try:
            self._device.disconnect()
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error disconnecting from Switchbot.", exc_info=True)
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
        self._last_time_command_send = time.time()
        if not write_result:
            _LOGGER.error(
                "Sent command but didn't get a response from Switchbot confirming command was sent."
                " Please check the Switchbot."
            )
        else:
            _LOGGER.info("Successfully sent command to Switchbot (MAC: %s).", self._mac)
        return write_result

    def _sendcommand(self, key, retry) -> bool:
        send_success = False
        command = self._commandkey(key)
        _LOGGER.debug("Sending command to switchbot %s", command)
        try:
            self._connect()
            send_success = self._writekey(command)
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error talking to Switchbot.", exc_info=True)
        finally:
            self._disconnect()
        if send_success:
            return True
        if retry < 1:
            _LOGGER.error(
                "Switchbot communication failed. Stopping trying.", exc_info=True
            )
            return False
        _LOGGER.warning(
            "Cannot connect to Switchbot. Retrying (remaining: %d)...", retry
        )
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._sendcommand(key, retry - 1)

    def get_servicedata(self, retry=DEFAULT_RETRY_COUNT, scan_timeout=5) -> bytearray:
        """Get BTLE 16b Service Data,
        returns after the given timeout period in seconds."""
        devices = None

        waiting_time = self._time_between_update_command - time.time()
        if waiting_time > 0:
            time.sleep(waiting_time)
        try:
            devices = bluepy.btle.Scanner().scan(scan_timeout)

        except bluepy.btle.BTLEManagementError:
            _LOGGER.warning("Error updating Switchbot.", exc_info=True)

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Switchbot update failed. Stopping trying.", exc_info=True
                )
                return None

            _LOGGER.warning(
                "Cannot update Switchbot. Retrying (remaining: %d)...", retry
            )
            time.sleep(DEFAULT_RETRY_TIMEOUT)
            return self.get_servicedata(retry - 1, scan_timeout)

        for device in devices:
            if self._mac.lower() == device.addr.lower():
                for (adtype, _, value) in device.getScanData():
                    if adtype == 22:
                        service_data = value[4:].encode()
                        service_data = binascii.unhexlify(service_data)

                        return service_data

        return None

    def get_mac(self) -> str:
        """Returns the mac address of the device."""
        return self._mac

    def get_min_time_update(self):
        """Returns the first time an update can be executed."""
        return self._last_time_command_send + self._time_between_update_command

    def get_battery_percent(self) -> int:
        """Returns device battery level in percent."""
        return self._battery_percent


class Switchbot(SwitchbotDevice):
    """Representation of a Switchbot."""

    def __init__(self, *args, **kwargs) -> None:
        self._is_on = None
        self._mode = None
        super().__init__(*args, **kwargs)

    def update(self, scan_timeout=5) -> None:
        """Updates the mode, battery percent and state of the device."""
        barray = self.get_servicedata(scan_timeout=scan_timeout)

        if barray is None:
            return

        _mode = barray[1] & 0b10000000  # 128 switch or 0 toggle
        if _mode != 0:
            self._mode = "switch"
        else:
            self._mode = "toggle"

        _is_on = barray[1] & 0b01000000  # 64 on or 0 for off
        if _is_on == 0 and self._mode == "switch":
            self._is_on = True
        else:
            self._is_on = False

        self._battery_percent = barray[2] & 0b01111111

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
        """Return Toggle or Switch from cache.
        Run update first."""
        return self._mode

    def is_on(self) -> bool:
        """Return switch state from cache.
        Run update first."""
        return self._is_on


class SwitchbotCurtain(SwitchbotDevice):
    """Representation of a Switchbot Curtain."""

    def __init__(self, *args, **kwargs) -> None:
        """Constructor for a Switchbot Curtain.
        The position of the curtain is saved in self._pos with 0 = open and 100 = closed.
        This is independent of the calibration of the curtain bot (Open left to right/
        Open right to left/Open from the middle).
        The parameter 'reverse_mode' reverse these values,
        if 'reverse_mode' = True, position = 0 equals close
        and position = 100 equals open. The parameter is default set to True so that
        the definition of position is the same as in Home Assistant."""
        self._reverse = kwargs.pop("reverse_mode", True)
        self._pos = 0
        self._light_level = 0
        self._is_calibrated = 0
        super().__init__(*args, **kwargs)

    def open(self) -> bool:
        """Send open command."""
        self._pos = 100 if self._reverse else 0
        return self._sendcommand(OPEN_KEY, self._retry_count)

    def close(self) -> bool:
        """Send close command."""
        self._pos = 0 if self._reverse else 100
        return self._sendcommand(CLOSE_KEY, self._retry_count)

    def stop(self) -> bool:
        """Send stop command to device."""
        return self._sendcommand(STOP_KEY, self._retry_count)

    def set_position(self, position: int) -> bool:
        """Send position command (0-100) to device."""
        position = (100 - position) if self._reverse else position
        self._pos = position
        hex_position = "%0.2X" % position
        return self._sendcommand(POSITION_KEY + hex_position, self._retry_count)

    def update(self, scan_timeout=5) -> None:
        """Updates the current position, battery percent and light level of the device."""
        barray = self.get_servicedata(scan_timeout=scan_timeout)

        if barray is None:
            return

        self._is_calibrated = barray[1] & 0b01000000
        self._battery_percent = barray[2] & 0b01111111
        position = max(min(barray[3] & 0b01111111, 100), 0)
        self._pos = (100 - position) if self._reverse else position
        self._light_level = (barray[4] >> 4) & 0b00001111  # light sensor level (1-10)

    def get_position(self) -> int:
        """Returns the current cached position (0-100), the actual position could vary.
        To get the actual position call update() first."""
        return self._pos

    def get_light_level(self) -> int:
        """Returns the current cached light level, the actual light level could vary.
        To get the actual light level call update() first."""
        return self._light_level

    def is_reversed(self) -> bool:
        """Returns True if the curtain open from left to right."""
        return self._reverse
