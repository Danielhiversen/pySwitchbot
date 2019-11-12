"""Library to handle connection with Switchbot"""

import binascii
import logging

import bluepy
import time

UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
HANDLE = "cba20002-224d-11e6-9fb8-0002a5d5c51b"

PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"

_LOGGER = logging.getLogger(__name__)


class Switchbot:
    """Representation of a Switchbot."""

    def __init__(self, mac) -> None:
        self._mac = mac
        self._device = None

    def _connect(self):
        if self._device is None:
            try:
                _LOGGER.debug("Connecting to Switchbot...")
                self._device = bluepy.btle.Peripheral(self._mac,
                                                      bluepy.btle.ADDR_TYPE_RANDOM)
                _LOGGER.debug("Connected to Switchbot.")
            except bluepy.btle.BTLEException:
                _LOGGER.warning("Failed connecting to Switchbot.", exc_info=True)
                self._device = None
                raise

    def _disconnect(self):
        if self._device is not None:
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
            _LOGGER.debug("Successfully sent command to Switchbot.")
        return write_result

    def _sendcommand(self, key, retry=3) -> bool:
        send_success = False
        try:
            self._connect()
            send_success = self._writekey(key)
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error talking to Switchbot.", exc_info=True)
        finally:
            self._disconnect()
        if not send_success:
            if retry < 1:
                _LOGGER.error("Switchbot communication failed. Stopping trying.", exc_info=True)
            else:
                _LOGGER.warning("Cannot connect to Switchbot. Retrying (remaining: %d)...", retry)
                time.sleep(.25)
                return self._sendcommand(key, retry - 1)
        return send_success

    def turn_on(self) -> None:
        """Turn device on."""
        return self._sendcommand(ON_KEY)

    def turn_off(self) -> None:
        """Turn device off."""
        return self._sendcommand(OFF_KEY)

    def press(self) -> None:
        """Press command to device."""
        return self._sendcommand(PRESS_KEY)
