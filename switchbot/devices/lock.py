"""Library to handle connection with Switchbot Lock."""
from __future__ import annotations

import logging
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from bleak import BLEDevice

from .device import SwitchbotDevice
from ..const import LockStatus

COMMAND_HEADER = "57"
COMMAND_GET_CK_IV = f"{COMMAND_HEADER}0f2103"
COMMAND_UNLOCK = f"{COMMAND_HEADER}0f4e01011080"
COMMAND_LOCK = f"{COMMAND_HEADER}0f4e01011000"

_LOGGER = logging.getLogger(__name__)


class SwitchbotLock(SwitchbotDevice):
    """Representation of a Switchbot Lock."""

    def __init__(self, device: BLEDevice, key_id: str, encryption_key: str, interface: int = 0, **kwargs: Any) -> None:
        if len(key_id) == 0:
            _LOGGER.error("key_id is missing")
        elif len(key_id) != 2:
            _LOGGER.error("invalid key_id")
        if len(encryption_key) == 0:
            _LOGGER.error("encryption_key is missing")
        elif len(encryption_key) != 32:
            _LOGGER.error("invalid encryption_key")
        self._iv = None
        self._cipher = None
        self._key_id = key_id
        self._encryption_key = bytearray.fromhex(encryption_key)
        super().__init__(device, None, interface, **kwargs)

    async def lock(self) -> bool:
        """Send lock command."""
        result = await self._send_command(COMMAND_LOCK)
        return self._check_command_result(result, 0, {1})

    async def unlock(self) -> bool:
        """Send unlock command."""
        result = await self._send_command(COMMAND_UNLOCK)
        return self._check_command_result(result, 0, {1})

    async def update(self, interface: int | None = None) -> None:
        await self.get_device_data(retry=self._retry_count, interface=interface)

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

    async def _send_command(self, key: str, retry: int | None = None, encrypt: bool = True) -> bytes | None:
        if not encrypt:
            return await super()._send_command(key[:2] + "000000" + key[2:], retry)

        result = await self._ensure_encryption_initialized()
        if not result:
            _LOGGER.error("Failed to initialize encryption")
            return None

        encrypted = key[:2] + self._key_id + self._iv[0:2].hex() + self._encrypt(key[2:])
        result = await super()._send_command(encrypted, retry)
        return result[:1] + self._decrypt(result[4:])

    async def _ensure_encryption_initialized(self) -> bool:
        if self._iv is not None:
            return True

        result = await self._send_command(COMMAND_GET_CK_IV + self._key_id, encrypt=False)
        ok = self._check_command_result(result, 0, {0x01})
        if ok:
            self._iv = result[4:]

        return ok

    async def _execute_disconnect(self) -> None:
        self._iv = None
        self._cipher = None
        await super()._execute_disconnect()

    def _get_cipher(self) -> Cipher:
        if self._cipher is None:
            self._cipher = Cipher(algorithms.AES128(self._encryption_key), modes.CTR(self._iv))
        return self._cipher

    def _encrypt(self, data: str) -> str:
        if len(data) == 0:
            return ""
        encryptor = self._get_cipher().encryptor()
        return (encryptor.update(bytearray.fromhex(data)) + encryptor.finalize()).hex()

    def _decrypt(self, data: bytearray) -> bytes:
        if len(data) == 0:
            return b''
        decryptor = self._get_cipher().decryptor()
        return decryptor.update(data) + decryptor.finalize()
