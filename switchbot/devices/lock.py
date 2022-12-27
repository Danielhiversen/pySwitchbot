"""Library to handle connection with Switchbot Lock."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from bleak.backends.device import BLEDevice
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..const import LockStatus
from .device import SwitchbotDevice

COMMAND_HEADER = "57"
COMMAND_GET_CK_IV = f"{COMMAND_HEADER}0f2103"
COMMAND_LOCK_INFO = f"{COMMAND_HEADER}0f4f8101"
COMMAND_UNLOCK = f"{COMMAND_HEADER}0f4e01011080"
COMMAND_LOCK = f"{COMMAND_HEADER}0f4e01011000"
COMMAND_ENABLE_NOTIFICATIONS = f"{COMMAND_HEADER}0e01001e00008101"
COMMAND_DISABLE_NOTIFICATIONS = f"{COMMAND_HEADER}0e00"

MOVING_STATUSES = {LockStatus.LOCKING, LockStatus.UNLOCKING}
BLOCKED_STATUSES = {LockStatus.LOCKING_STOP, LockStatus.UNLOCKING_STOP}
REST_STATUSES = {LockStatus.LOCKED, LockStatus.UNLOCKED, LockStatus.NOT_FULLY_LOCKED}

_LOGGER = logging.getLogger(__name__)


class SwitchbotLock(SwitchbotDevice):
    """Representation of a Switchbot Lock."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        **kwargs: Any,
    ) -> None:
        if len(key_id) == 0:
            raise ValueError("key_id is missing")
        elif len(key_id) != 2:
            raise ValueError("key_id is invalid")
        if len(encryption_key) == 0:
            raise ValueError("encryption_key is missing")
        elif len(encryption_key) != 32:
            raise ValueError("encryption_key is invalid")
        self._iv = None
        self._cipher = None
        self._key_id = key_id
        self._encryption_key = bytearray.fromhex(encryption_key)
        self._notifications_enabled: bool = False
        super().__init__(device, None, interface, **kwargs)

    async def lock(self) -> bool:
        """Send lock command."""
        return await self._lock_unlock(
            COMMAND_LOCK, {LockStatus.LOCKED, LockStatus.LOCKING}
        )

    async def unlock(self) -> bool:
        """Send unlock command."""
        return await self._lock_unlock(
            COMMAND_UNLOCK, {LockStatus.UNLOCKED, LockStatus.UNLOCKING}
        )

    async def _lock_unlock(
        self, command: str, ignore_statuses: set[LockStatus]
    ) -> bool:
        status = self.get_lock_status()
        if status is None:
            await self.update()
            status = self.get_lock_status()
        if status in ignore_statuses:
            return True

        await self._enable_notifications()
        result = await self._send_command(command)
        if not self._check_command_result(result, 0, {1}):
            return False
        return True

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic status."""
        lock_raw_data = await self._get_lock_info()
        if not lock_raw_data:
            return None

        basic_data = await self._get_basic_info()
        if not basic_data:
            return None

        lock_data = self._parse_lock_data(lock_raw_data[1:])
        lock_data.update(battery=basic_data[1], firmware=basic_data[2] / 10.0)

        return lock_data

    def is_calibrated(self) -> Any:
        """Return True if lock is calibrated."""
        return self._get_adv_value("calibration")

    def get_lock_status(self) -> LockStatus:
        """Return lock status."""
        return self._get_adv_value("status")

    def is_door_open(self) -> bool:
        """Return True if door is open."""
        return self._get_adv_value("door_open")

    def is_unclosed_alarm_on(self) -> bool:
        """Return True if unclosed door alarm is on."""
        return self._get_adv_value("unclosed_alarm")

    def is_unlocked_alarm_on(self) -> bool:
        """Return True if lock unlocked alarm is on."""
        return self._get_adv_value("unlocked_alarm")

    def is_auto_lock_paused(self) -> bool:
        """Return True if auto lock is paused."""
        return self._get_adv_value("auto_lock_paused")

    async def _get_lock_info(self) -> bytes | None:
        """Return lock info of device."""
        _data = await self._send_command(key=COMMAND_LOCK_INFO, retry=self._retry_count)

        if not self._check_command_result(_data, 0, {1}):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    async def _enable_notifications(self) -> bool:
        if self._notifications_enabled:
            return True
        result = await self._send_command(COMMAND_ENABLE_NOTIFICATIONS)
        if self._check_command_result(result, 0, {1}):
            self._notifications_enabled = True
        return self._notifications_enabled

    async def _disable_notifications(self) -> bool:
        if not self._notifications_enabled:
            return True
        result = await self._send_command(COMMAND_DISABLE_NOTIFICATIONS)
        if self._check_command_result(result, 0, {1}):
            self._notifications_enabled = False
        return not self._notifications_enabled

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        if self._notifications_enabled and self._check_command_result(data, 0, {0xF}):
            self._update_lock_status(data)
        else:
            super()._notification_handler(_sender, data)

    def _update_lock_status(self, data: bytearray) -> None:
        data = self._decrypt(data[4:])
        lock_data = self._parse_lock_data(data)
        current_status = self.get_lock_status()
        if (
            lock_data["status"] != current_status or current_status not in REST_STATUSES
        ) and (
            lock_data["status"] in REST_STATUSES
            or lock_data["status"] in BLOCKED_STATUSES
        ):
            asyncio.create_task(self._disable_notifications())

        self._update_parsed_data(lock_data)
        self._fire_callbacks()

    @staticmethod
    def _parse_lock_data(data: bytes) -> dict[str, Any]:
        return {
            "calibration": bool(data[0] & 0b10000000),
            "status": LockStatus((data[0] & 0b01110000) >> 4),
            "door_open": bool(data[0] & 0b00000100),
            "unclosed_alarm": bool(data[1] & 0b00100000),
            "unlocked_alarm": bool(data[1] & 0b00010000),
        }

    async def _send_command(
        self, key: str, retry: int | None = None, encrypt: bool = True
    ) -> bytes | None:
        if not encrypt:
            return await super()._send_command(key[:2] + "000000" + key[2:], retry)

        result = await self._ensure_encryption_initialized()
        if not result:
            _LOGGER.error("Failed to initialize encryption")
            return None

        encrypted = (
            key[:2] + self._key_id + self._iv[0:2].hex() + self._encrypt(key[2:])
        )
        result = await super()._send_command(encrypted, retry)
        return result[:1] + self._decrypt(result[4:])

    async def _ensure_encryption_initialized(self) -> bool:
        if self._iv is not None:
            return True

        result = await self._send_command(
            COMMAND_GET_CK_IV + self._key_id, encrypt=False
        )
        ok = self._check_command_result(result, 0, {0x01})
        if ok:
            self._iv = result[4:]

        return ok

    async def _execute_disconnect(self) -> None:
        await super()._execute_disconnect()
        self._iv = None
        self._cipher = None
        self._notifications_enabled = False

    def _get_cipher(self) -> Cipher:
        if self._cipher is None:
            self._cipher = Cipher(
                algorithms.AES128(self._encryption_key), modes.CTR(self._iv)
            )
        return self._cipher

    def _encrypt(self, data: str) -> str:
        if len(data) == 0:
            return ""
        encryptor = self._get_cipher().encryptor()
        return (encryptor.update(bytearray.fromhex(data)) + encryptor.finalize()).hex()

    def _decrypt(self, data: bytearray) -> bytes:
        if len(data) == 0:
            return b""
        decryptor = self._get_cipher().decryptor()
        return decryptor.update(data) + decryptor.finalize()
