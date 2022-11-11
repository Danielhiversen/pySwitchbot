"""Library to handle connection with Switchbot."""
from __future__ import annotations

import asyncio
import binascii
import logging
from enum import Enum
from typing import Any, Callable
from uuid import UUID

import async_timeout
from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import (
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    BleakNotFoundError,
    ble_device_has_changed,
    establish_connection,
)

from ..const import DEFAULT_RETRY_COUNT, DEFAULT_SCAN_TIMEOUT
from ..discovery import GetSwitchbotDevices
from ..models import SwitchBotAdvertisement

_LOGGER = logging.getLogger(__name__)

REQ_HEADER = "570f"


# Keys common to all device types
DEVICE_GET_BASIC_SETTINGS_KEY = "5702"
DEVICE_SET_MODE_KEY = "5703"
DEVICE_SET_EXTENDED_KEY = REQ_HEADER

# Base key when encryption is set
KEY_PASSWORD_PREFIX = "571"


# How long to hold the connection
# to wait for additional commands for
# disconnecting the device.
DISCONNECT_DELAY = 8.5


class ColorMode(Enum):

    OFF = 0
    COLOR_TEMP = 1
    RGB = 2
    EFFECT = 3


class CharacteristicMissingError(Exception):
    """Raised when a characteristic is missing."""


class SwitchbotOperationError(Exception):
    """Raised when an operation fails."""


def _sb_uuid(comms_type: str = "service") -> UUID | str:
    """Return Switchbot UUID."""

    _uuid = {"tx": "002", "rx": "003", "service": "d00"}

    if comms_type in _uuid:
        return UUID(f"cba20{_uuid[comms_type]}-224d-11e6-9fb8-0002a5d5c51b")

    return "Incorrect type, choose between: tx, rx or service"


READ_CHAR_UUID = _sb_uuid(comms_type="rx")
WRITE_CHAR_UUID = _sb_uuid(comms_type="tx")


class SwitchbotBaseDevice:
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
        self._override_adv_data: dict[str, Any] | None = None
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
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._expected_disconnect = False
        self.loop = asyncio.get_event_loop()
        self._callbacks: list[Callable[[], None]] = []
        self._notify_future: asyncio.Future[bytearray] | None = None

    def advertisement_changed(self, advertisement: SwitchBotAdvertisement) -> bool:
        """Check if the advertisement has changed."""
        return bool(
            not self._sb_adv_data
            or ble_device_has_changed(self._sb_adv_data.device, advertisement.device)
            or advertisement.data != self._sb_adv_data.data
        )

    def _commandkey(self, key: str) -> str:
        """Add password to key if set."""
        if self._password_encoded is None:
            return key
        key_action = key[3]
        key_suffix = key[4:]
        return KEY_PASSWORD_PREFIX + key_action + self._password_encoded + key_suffix

    async def _send_command(self, key: str, retry: int | None = None) -> bytes | None:
        """Send command to device and read response."""
        if retry is None:
            retry = self._retry_count
        command = bytearray.fromhex(self._commandkey(key))
        _LOGGER.debug("%s: Scheduling command %s", self.name, command.hex())
        max_attempts = retry + 1
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            for attempt in range(max_attempts):
                try:
                    return await self._send_command_locked(key, command)
                except BleakNotFoundError:
                    _LOGGER.error(
                        "%s: device not found, no longer in range, or poor RSSI: %s",
                        self.name,
                        self.rssi,
                        exc_info=True,
                    )
                    raise
                except CharacteristicMissingError as ex:
                    if attempt == retry:
                        _LOGGER.error(
                            "%s: characteristic missing: %s; Stopping trying; RSSI: %s",
                            self.name,
                            ex,
                            self.rssi,
                            exc_info=True,
                        )
                        raise

                    _LOGGER.debug(
                        "%s: characteristic missing: %s; RSSI: %s",
                        self.name,
                        ex,
                        self.rssi,
                        exc_info=True,
                    )
                except BLEAK_RETRY_EXCEPTIONS:
                    if attempt == retry:
                        _LOGGER.error(
                            "%s: communication failed; Stopping trying; RSSI: %s",
                            self.name,
                            self.rssi,
                            exc_info=True,
                        )
                        raise

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
        if self._sb_adv_data:
            return self._sb_adv_data.rssi
        return self._device.rssi

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
                use_services_cache=True,
                ble_device_callback=lambda: self._device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                resolved = self._resolve_characteristics(await client.get_services())
            self._client = client
            self._reset_disconnect_timer()
            await self._start_notify()

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> bool:
        """Resolve characteristics."""
        self._read_char = services.get_characteristic(READ_CHAR_UUID)
        self._write_char = services.get_characteristic(WRITE_CHAR_UUID)
        return bool(self._read_char and self._write_char)

    def _reset_disconnect_timer(self):
        """Reset disconnect timer."""
        self._cancel_disconnect_timer()
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
        self._cancel_disconnect_timer()
        asyncio.create_task(self._execute_timed_disconnect())

    def _cancel_disconnect_timer(self):
        """Cancel disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None

    async def _execute_forced_disconnect(self) -> None:
        """Execute forced disconnection."""
        self._cancel_disconnect_timer()
        _LOGGER.debug(
            "%s: Executing forced disconnect",
            self.name,
        )
        await self._execute_disconnect()

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Executing timed disconnect after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            if self._disconnect_timer:  # If the timer was reset, don't disconnect
                return
            client = self._client
            self._expected_disconnect = True
            self._client = None
            self._read_char = None
            self._write_char = None
            if client and client.is_connected:
                _LOGGER.debug("%s: Disconnecting", self.name)
                await client.disconnect()
                _LOGGER.debug("%s: Disconnect completed", self.name)

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
            await self._execute_forced_disconnect()
            raise
        except BleakError as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_forced_disconnect()
            raise

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        if self._notify_future and not self._notify_future.done():
            self._notify_future.set_result(data)
            return
        _LOGGER.debug("%s: Received unsolicited notification: %s", self.name, data)

    async def _start_notify(self) -> None:
        """Start notification."""
        _LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
        await self._client.start_notify(self._read_char, self._notification_handler)

    async def _execute_command_locked(self, key: str, command: bytes) -> bytes:
        """Execute command and read response."""
        assert self._client is not None
        if not self._read_char:
            raise CharacteristicMissingError(READ_CHAR_UUID)
        if not self._write_char:
            raise CharacteristicMissingError(WRITE_CHAR_UUID)
        self._notify_future = asyncio.Future()
        client = self._client

        _LOGGER.debug("%s: Sending command: %s", self.name, key)
        await client.write_gatt_char(self._write_char, command, False)

        async with async_timeout.timeout(5):
            notify_msg = await self._notify_future
        _LOGGER.debug("%s: Notification received: %s", self.name, notify_msg.hex())
        self._notify_future = None

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
        if self._override_adv_data and key in self._override_adv_data:
            _LOGGER.debug(
                "%s: Using override value for %s: %s",
                self.name,
                key,
                self._override_adv_data[key],
            )
            return self._override_adv_data[key]
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data.data["data"].get(key)

    def get_battery_percent(self) -> Any:
        """Return device battery level in percent."""
        return self._get_adv_value("battery")

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        # Only accept advertisements if the data is not missing
        # if we already have an advertisement with data
        self._device = advertisement.device

    async def get_device_data(
        self, retry: int | None = None, interface: int | None = None
    ) -> SwitchBotAdvertisement | None:
        """Find switchbot devices and their advertisement data."""
        if retry is None:
            retry = self._retry_count

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
        _data = await self._send_command(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    def _fire_callbacks(self) -> None:
        """Fire callbacks."""
        _LOGGER.debug("%s: Fire callbacks", self.name)
        for callback in self._callbacks:
            callback()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to device notifications."""
        self._callbacks.append(callback)

        def _unsub() -> None:
            """Unsubscribe from device notifications."""
            self._callbacks.remove(callback)

        return _unsub

    async def update(self) -> None:
        """Update state of device."""

    def _check_command_result(
        self, result: bytes | None, index: int, values: set[int]
    ) -> bool:
        """Check command result."""
        if not result or len(result) - 1 < index:
            result_hex = result.hex() if result else "None"
            raise SwitchbotOperationError(
                f"{self.name}: Sending command failed (result={result_hex} index={index} expected={values} rssi={self.rssi})"
            )
        return result[index] in values

    def _set_advertisement_data(self, advertisement: SwitchBotAdvertisement) -> None:
        """Set advertisement data."""
        if advertisement.data.get("data") or not self._sb_adv_data.data.get("data"):
            self._sb_adv_data = advertisement
        self._override_adv_data = None

    def switch_mode(self) -> bool | None:
        """Return true or false from cache."""
        # To get actual position call update() first.
        return self._get_adv_value("switchMode")


class SwitchbotDevice(SwitchbotBaseDevice):
    """Base Representation of a Switchbot Device.

    This base class consumes the advertisement data during connection. If the device
    sends stale advertisement data while connected, use
    SwitchbotDeviceOverrideStateDuringConnection instead.
    """

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        super().update_from_advertisement(advertisement)
        self._set_advertisement_data(advertisement)


class SwitchbotDeviceOverrideStateDuringConnection(SwitchbotBaseDevice):
    """Base Representation of a Switchbot Device.

    This base class ignores the advertisement data during connection and uses the
    data from the device instead.
    """

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        super().update_from_advertisement(advertisement)
        if self._client and self._client.is_connected:
            # We do not consume the advertisement data if we are connected
            # to the device. This is because the advertisement data is not
            # updated when the device is connected for some devices.
            _LOGGER.debug("%s: Ignore advertisement data during connection", self.name)
            return
        self._set_advertisement_data(advertisement)


class SwitchbotSequenceDevice(SwitchbotDevice):
    """A Switchbot sequence device.

    This class must not use SwitchbotDeviceOverrideStateDuringConnection because
    it needs to know when the sequence_number has changed.
    """

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        current_state = self._get_adv_value("sequence_number")
        super().update_from_advertisement(advertisement)
        new_state = self._get_adv_value("sequence_number")
        _LOGGER.debug(
            "%s: update advertisement: %s (seq before: %s) (seq after: %s)",
            self.name,
            advertisement,
            current_state,
            new_state,
        )
        if current_state != new_state:
            asyncio.ensure_future(self.update())
