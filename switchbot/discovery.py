"""Discover switchbot devices."""

from __future__ import annotations

import asyncio
import logging

import bleak
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parser import parse_advertisement_data
from .const import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_TIMEOUT, DEFAULT_SCAN_TIMEOUT
from .models import SwitchBotAdvertisement

_LOGGER = logging.getLogger(__name__)
CONNECT_LOCK = asyncio.Lock()


class GetSwitchbotDevices:
    """Scan for all Switchbot devices and return by type."""

    def __init__(self, interface: int = 0) -> None:
        """Get switchbot devices class constructor."""
        self._interface = f"hci{interface}"
        self._adv_data: dict[str, SwitchBotAdvertisement] = {}

    def detection_callback(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> None:
        """Callback for device detection."""
        discovery = parse_advertisement_data(device, advertisement_data)
        if discovery:
            self._adv_data[discovery.address] = discovery

    async def discover(
        self, retry: int = DEFAULT_RETRY_COUNT, scan_timeout: int = DEFAULT_SCAN_TIMEOUT
    ) -> dict:
        """Find switchbot devices and their advertisement data."""

        devices = None
        devices = bleak.BleakScanner(
            detection_callback=self.detection_callback,
            # TODO: Find new UUIDs to filter on. For example, see
            # https://github.com/OpenWonderLabs/SwitchBotAPI-BLE/blob/4ad138bb09f0fbbfa41b152ca327a78c1d0b6ba9/devicetypes/meter.md
            adapter=self._interface,
        )

        async with CONNECT_LOCK:
            await devices.start()
            await asyncio.sleep(scan_timeout)
            await devices.stop()

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Scanning for Switchbot devices failed. Stop trying", exc_info=True
                )
                return self._adv_data

            _LOGGER.warning(
                "Error scanning for Switchbot devices. Retrying (remaining: %d)",
                retry,
            )
            await asyncio.sleep(DEFAULT_RETRY_TIMEOUT)
            return await self.discover(retry - 1, scan_timeout)

        return self._adv_data

    async def _get_devices_by_model(
        self,
        model: str,
    ) -> dict:
        """Get switchbot devices by type."""
        if not self._adv_data:
            await self.discover()

        return {
            address: adv
            for address, adv in self._adv_data.items()
            if adv.data.get("model") == model
        }

    async def get_blind_tilts(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoBlindTilt/BlindTilts devices with services data."""
        regular_blinds = await self._get_devices_by_model("x")
        pairing_blinds = await self._get_devices_by_model("X")
        return {**regular_blinds, **pairing_blinds}

    async def get_curtains(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoCurtain/Curtains devices with services data."""
        regular_curtains = await self._get_devices_by_model("c")
        pairing_curtains = await self._get_devices_by_model("C")
        regular_curtains3 = await self._get_devices_by_model("{")
        pairing_curtains3 = await self._get_devices_by_model("[")
        return {
            **regular_curtains,
            **pairing_curtains,
            **regular_curtains3,
            **pairing_curtains3,
        }

    async def get_bots(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoHand/Bot devices with services data."""
        return await self._get_devices_by_model("H")

    async def get_tempsensors(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoSensorTH/Temp sensor devices with services data."""
        base_meters = await self._get_devices_by_model("T")
        plus_meters = await self._get_devices_by_model("i")
        io_meters = await self._get_devices_by_model("w")
        hub2_meters = await self._get_devices_by_model("v")
        return {**base_meters, **plus_meters, **io_meters, **hub2_meters}

    async def get_contactsensors(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoContact/Contact sensor devices with services data."""
        return await self._get_devices_by_model("d")

    async def get_leakdetectors(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all Leak Detectors with services data."""
        return await self._get_devices_by_model("&")

    async def get_locks(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoLock/Locks devices with services data."""
        locks = await self._get_devices_by_model("o")
        lock_pros = await self._get_devices_by_model("$")
        return {**locks, **lock_pros}

    async def get_keypads(self) -> dict[str, SwitchBotAdvertisement]:
        """Return all WoKeypad/Keypad devices with services data."""
        return await self._get_devices_by_model("y")

    async def get_device_data(
        self, address: str
    ) -> dict[str, SwitchBotAdvertisement] | None:
        """Return data for specific device."""
        if not self._adv_data:
            await self.discover()

        return {
            device: adv
            for device, adv in self._adv_data.items()
            # MacOS uses UUIDs instead of MAC addresses
            if adv.data.get("address") == address
        }
