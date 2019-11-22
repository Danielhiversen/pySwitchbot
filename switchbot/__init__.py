"""Library to handle connection with Switchbot"""
import time

import binascii
import logging

import bluepy

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = .2

UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
HANDLE = "cba20002-224d-11e6-9fb8-0002a5d5c51b"

PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"

_LOGGER = logging.getLogger(__name__)


class Switchbot:
    """Representation of a Switchbot."""

    def __init__(self, mac, retry_count=DEFAULT_RETRY_COUNT) -> None:
        self._mac = mac
        self._device = None
        self._retry_count = retry_count

    def _connect(self) -> None:
        if self._device is not None:
            return
        try:
            _LOGGER.debug("Connecting to Switchbot...")
            self._device = bluepy.btle.Peripheral(self._mac,
                                                  bluepy.btle.ADDR_TYPE_RANDOM)
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

    def _writekey(self, key) -> bool:
        _LOGGER.debug("Prepare to send")
        hand_service = self._device.getServiceByUUID(UUID)
        hand = hand_service.getCharacteristics(HANDLE)[0]
        _LOGGER.debug("Sending command, %s", key)
        write_result = hand.write(binascii.a2b_hex(key), withResponse=True)
        if not write_result:
            _LOGGER.error("Sent command but didn't get a response from Switchbot confirming command was sent. "
                          "Please check the Switchbot.")
        else:
            _LOGGER.info("Successfully sent command to Switchbot (MAC: %s).", self._mac)
        return write_result

    def _sendcommand(self, key, retry) -> bool:
        send_success = False
        try:
            self._connect()
            send_success = self._writekey(key)
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error talking to Switchbot.", exc_info=True)
        finally:
            self._disconnect()
        if send_success:
            return send_success
        if retry < 1:
            _LOGGER.error("Switchbot communication failed. Stopping trying.", exc_info=True)
            return False
        _LOGGER.warning("Cannot connect to Switchbot. Retrying (remaining: %d)...", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._sendcommand(key, retry - 1)

    def turn_on(self) -> bool:
        """Turn device on."""
        return self._sendcommand(ON_KEY, self._retry_count)

    def turn_off(self) -> bool:
        """Turn device off."""
        return self._sendcommand(OFF_KEY, self._retry_count)

    def press(self) -> bool:
        """Press command to device."""
        return self._sendcommand(PRESS_KEY, self._retry_count)
