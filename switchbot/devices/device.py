"""Library to handle connection with Switchbot."""
from __future__ import annotations

import asyncio
import binascii
import logging
from typing import Any
from uuid import UUID

import async_timeout

from bleak import BleakError
from bleak.exc import BleakDBusError
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakNotFoundError,
    ble_device_has_changed,
    establish_connection,
)

from ..const import DEFAULT_RETRY_COUNT, DEFAULT_SCAN_TIMEOUT
from ..discovery import GetSwitchbotDevices
from ..models import SwitchBotAdvertisement

_LOGGER = logging.getLogger(__name__)

# Keys common to all device types
DEVICE_GET_BASIC_SETTINGS_KEY = "5702"
DEVICE_SET_MODE_KEY = "5703"
DEVICE_SET_EXTENDED_KEY = "570f"

# Base key when encryption is set
KEY_PASSWORD_PREFIX = "571"

BLEAK_EXCEPTIONS = (AttributeError, BleakError, asyncio.exceptions.TimeoutError)

# How long to hold the connection
# to wait for additional commands for
# disconnecting the device.
DISCONNECT_DELAY = 49


def _sb_uuid(comms_type: str = "service") -> UUID | str:
    """Return Switchbot UUID."""

    _uuid = {"tx": "002", "rx": "003", "service": "d00"}

    if comms_type in _uuid:
        return UUID(f"cba20{_uuid[comms_type]}-224d-11e6-9fb8-0002a5d5c51b")

    return "Incorrect type, choose between: tx, rx or service"


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
        self._connect_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        if password is None or password == "":
            self._password_encoded = None
        else:
            self._password_encoded = "%08x" % (
                binascii.crc32(password.encode("ascii")) & 0xFFFFFFFF
            )
        self._client: BleakClientWithServiceCache | None = None
        self._cached_services: BleakGATTServiceCollection | None = None
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._expected_disconnect = False
        self.loop = asyncio.get_event_loop()

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
        _LOGGER.debug("%s: Sending command %s", self.name, command)
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )

        max_attempts = retry + 1
        async with self._operation_lock:
            for attempt in range(max_attempts):
                try:
                    return await self._send_command_locked(key, command)
                except BleakNotFoundError:
                    _LOGGER.error(
                        "%s: device not found or no longer in range; Try restarting Bluetooth",
                        self.name,
                        exc_info=True,
                    )
                    return b"\x00"
                except BLEAK_EXCEPTIONS:
                    if attempt == retry:
                        _LOGGER.error(
                            "%s: communication failed; Stopping trying; RSSI: %s",
                            self.name,
                            self.rssi,
                            exc_info=True,
                        )
                        return b"\x00"

                    _LOGGER.debug(
                        "%s: communication failed with:", self.name, exc_info=True
                    )

        raise RuntimeError("Unreachable")

    @property
    def name(self) -> str:
        """Return device name."""
        return f"{self._device.name} ({self._device.address})"

    @property
    def rssi(self) -> int:
        """Return RSSI of device."""
        return self._get_adv_value("rssi")

    async def _ensure_connected(self):
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                self._disconnected,
                cached_services=self._cached_services,
                ble_device_callback=lambda: self._device,
            )
            self._cached_services = client.services
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            services = client.services
            self._read_char = services.get_characteristic(_sb_uuid(comms_type="rx"))
            self._write_char = services.get_characteristic(_sb_uuid(comms_type="tx"))
            self._client = client
            self._reset_disconnect_timer()

    def _reset_disconnect_timer(self):
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
        )

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "%s: Disconnected from device; RSSI: %s", self.name, self.rssi
            )
            return
        _LOGGER.warning(
            "%s: Device unexpectedly disconnected; RSSI: %s",
            self.name,
            self.rssi,
        )

    def _disconnect(self):
        """Disconnect from device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_timed_disconnect())

    async def _execute_timed_disconnect(self):
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Disconnecting after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self):
        """Execute disconnection."""
        async with self._connect_lock:
            if not self._client or not self._client.is_connected:
                return
            self._expected_disconnect = True
            await self._client.disconnect()
            self._client = None
            self._read_char = None
            self._write_char = None

    async def _send_command_locked(self, key: str, command: bytes) -> bytes:
        """Send command to device and read response."""
        await self._ensure_connected()
        try:
            return await self._execute_command_locked(key, command)
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(0.25)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.name,
                self.rssi,
                0.25,
                ex,
            )
            await self._execute_disconnect()
        except BleakError as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_disconnect()
            raise

    async def _execute_command_locked(self, key: str, command: bytes) -> bytes:
        """Execute command and read response."""
        assert self._client is not None
        assert self._read_char is not None
        assert self._write_char is not None
        future: asyncio.Future[bytearray] = asyncio.Future()
        client = self._client

        def _notification_handler(_sender: int, data: bytearray) -> None:
            """Handle notification responses."""
            if future.done():
                _LOGGER.debug("%s: Notification handler already done", self.name)
                return
            future.set_result(data)

        _LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
        await client.start_notify(self._read_char, _notification_handler)

        _LOGGER.debug("%s: Sending command: %s", self.name, key)
        await client.write_gatt_char(self._write_char, command, False)

        async with async_timeout.timeout(5):
            notify_msg = await future
        _LOGGER.debug("%s: Notification received: %s", self.name, notify_msg)

        _LOGGER.debug("%s: UnSubscribe to notifications", self.name)
        await client.stop_notify(self._read_char)

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
        if self._device and ble_device_has_changed(self._device, advertisement.device):
            self._cached_services = None
        self._device = advertisement.device

    async def get_device_data(
        self, retry: int = DEFAULT_RETRY_COUNT, interface: int | None = None
    ) -> SwitchBotAdvertisement | None:
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

    async def _get_basic_info(self) -> bytes | None:
        """Return basic info of device."""
        _data = await self._sendcommand(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data
