import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..const import SwitchbotModel
from ..models import SwitchBotAdvertisement
from .device import SwitchbotEncryptedDevice

_LOGGER = logging.getLogger(__name__)

COMMAND_HEADER = "57"
COMMAND_GET_CK_IV = f"{COMMAND_HEADER}0f2103"
COMMAND_TURN_OFF = f"{COMMAND_HEADER}0f70010000"
COMMAND_TURN_ON = f"{COMMAND_HEADER}0f70010100"
COMMAND_TOGGLE = f"{COMMAND_HEADER}0f70010200"
COMMAND_GET_VOLTAGE_AND_CURRENT = f"{COMMAND_HEADER}0f7106000000"
COMMAND_GET_SWITCH_STATE = f"{COMMAND_HEADER}0f7101000000"
PASSIVE_POLL_INTERVAL = 10 * 60


class SwitchbotRelaySwitch(SwitchbotEncryptedDevice):
    """Representation of a Switchbot relay switch 1pm."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.RELAY_SWITCH_1PM,
        **kwargs: Any,
    ) -> None:
        self._force_next_update = False
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.RELAY_SWITCH_1PM,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    def update_from_advertisement(self, advertisement: SwitchBotAdvertisement) -> None:
        """Update device data from advertisement."""
        # Obtain voltage and current through command.
        adv_data = advertisement.data["data"]
        if previous_voltage := self._get_adv_value("voltage"):
            adv_data["voltage"] = previous_voltage
        if previous_current := self._get_adv_value("current"):
            adv_data["current"] = previous_current
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
            self._force_next_update = True

    async def update(self, interface: int | None = None) -> None:
        """Update state of device."""
        if info := await self.get_voltage_and_current():
            self._last_full_update = time.monotonic()
            self._update_parsed_data(info)
            self._fire_callbacks()

    async def get_voltage_and_current(self) -> dict[str, Any] | None:
        """Get voltage and current because advtisement don't have these"""
        result = await self._send_command(COMMAND_GET_VOLTAGE_AND_CURRENT)
        ok = self._check_command_result(result, 0, {1})
        if ok:
            return {
                "voltage": ((result[9] << 8) + result[10]) / 10,
                "current": (result[11] << 8) + result[12],
            }
        return None

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get the current state of the switch."""
        result = await self._send_command(COMMAND_GET_SWITCH_STATE)
        if self._check_command_result(result, 0, {1}):
            return {
                "is_on": result[1] & 0x01 != 0,
            }
        return None

    def poll_needed(self, seconds_since_last_poll: float | None) -> bool:
        """Return if device needs polling."""
        if self._force_next_update:
            self._force_next_update = False
            return True
        if (
            seconds_since_last_poll is not None
            and seconds_since_last_poll < PASSIVE_POLL_INTERVAL
        ):
            return False
        time_since_last_full_update = time.monotonic() - self._last_full_update
        if time_since_last_full_update < PASSIVE_POLL_INTERVAL:
            return False
        return True

    async def turn_on(self) -> bool:
        """Turn device on."""
        result = await self._send_command(COMMAND_TURN_ON)
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._override_state({"isOn": True})
            self._fire_callbacks()
        return ok

    async def turn_off(self) -> bool:
        """Turn device off."""
        result = await self._send_command(COMMAND_TURN_OFF)
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._override_state({"isOn": False})
            self._fire_callbacks()
        return ok

    async def async_toggle(self, **kwargs) -> bool:
        """Toggle device."""
        result = await self._send_command(COMMAND_TOGGLE)
        status = self._check_command_result(result, 0, {1})
        return status

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        return self._get_adv_value("isOn")

    async def _send_command(
        self, key: str, retry: int | None = None, encrypt: bool = True
    ) -> bytes | None:
        if not encrypt:
            return await super()._send_command(key[:2] + "000000" + key[2:], retry)

        result = await self._ensure_encryption_initialized()
        if not result:
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
        ok = self._check_command_result(result, 0, {1})
        if ok:
            self._iv = result[4:]

        return ok

    async def _execute_disconnect(self) -> None:
        await super()._execute_disconnect()
        self._iv = None
        self._cipher = None

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
