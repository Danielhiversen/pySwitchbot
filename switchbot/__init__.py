"""Library to handle connection with Switchbot"""

import binascii
import logging

import bluepy

UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
HANDLE = "cba20002-224d-11e6-9fb8-0002a5d5c51b"

PRESS_KEY = "570100"
ON_KEY = "570101"
OFF_KEY = "570102"

_LOGGER = logging.getLogger(__name__)


class Switchbot:
    """Representation of a Switchmate."""

    def __init__(self, mac) -> None:
        self._mac = mac

    def _sendpacket(self, key, retry=2) -> bool:
        try:
            _LOGGER.debug("Connecting")
            device = bluepy.btle.Peripheral(self._mac,
                                            bluepy.btle.ADDR_TYPE_RANDOM)
            hand_service = device.getServiceByUUID(UUID)
            hand = hand_service.getCharacteristics(HANDLE)[0]
            _LOGGER.debug("Sending command, %s", key)
            hand.write(binascii.a2b_hex(key))
            _LOGGER.debug("Disconnecting")
            device.disconnect()
        except bluepy.btle.BTLEException:
            _LOGGER.error("Cannot connect to switchbot. Retrying", exc_info=True)
            if retry < 1:
                _LOGGER.error("Cannot connect to switchbot.", exc_info=True)
                return False
            return self._sendpacket(key, retry-1)
        return True

    def turn_on(self) -> None:
        """Turn device on."""
        return self._sendpacket(ON_KEY)

    def turn_off(self) -> None:
        """Turn device off."""
        return self._sendpacket(OFF_KEY)

    def press(self) -> None:
        """Press command to device."""
        return self._sendpacket(PRESS_KEY)
