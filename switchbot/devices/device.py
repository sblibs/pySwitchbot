"""Library to handle connection with Switchbot."""
from __future__ import annotations

import asyncio
import binascii
import logging
from ctypes import cast
from typing import Any, Callable, TypeVar
from uuid import UUID

import async_timeout
import bleak
from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak_retry_connector import (
    BleakClientWithServiceCache,
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
DISCONNECT_DELAY = 90


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
        _LOGGER.debug("Sending command to switchbot %s", command)
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete.",
                self.name,
            )

        max_attempts = retry + 1
        async with self._operation_lock:
            for attempt in range(max_attempts):
                try:
                    return await self._send_command_locked(key, command)
                except BLEAK_EXCEPTIONS(
                    bleak.BleakError, asyncio.exceptions.TimeoutError
                ):
                    if attempt == retry:
                        _LOGGER.error(
                            "Switchbot communication failed. Stopping trying",
                            exc_info=True,
                        )
                        return b"\x00"

                    _LOGGER.debug("Switchbot communication failed with:", exc_info=True)

        raise RuntimeError("Unreachable")

    @property
    def name(self) -> str:
        """Return device name."""
        return f"{self._device.name} ({self._device.address})"

    async def _ensure_connected(self):
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete.",
                self.name,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                cached_services=self._cached_services,
            )
            self._cached_services = client.services
            _LOGGER.debug("%s: Connected to SwitchBot Device", self.name)
            services = client.services
            self._read_char = services.get_characteristic(_sb_uuid(comms_type="rx"))
            self._write_char = services.get_characteristic(_sb_uuid(comms_type="tx"))
            self._client = client
            self._reset_disconnect_timer()

    def _reset_disconnect_timer(self):
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
        )

    def _disconnect(self):
        """Disconnect from device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_disconnect())

    async def _execute_disconnect(self):
        """Execute disconnection."""
        _LOGGER.debug(
            "%s: Disconnecting from SwitchBot Device after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        async with self._connect_lock:
            if not self._client or not self._client.is_connected:
                return
            await self._client.disconnect()
            self._client = None
            self._read_char = None
            self._write_char = None

    async def _send_command_locked(self, key: str, command: bytes) -> bytes:
        """Send command to device and read response."""
        client: BleakClientWithServiceCache | None = None
        await self._ensure_connected()
        client = self._client
        future: asyncio.Future[bytearray] = asyncio.Future()

        def _notification_handler(_sender: int, data: bytearray) -> None:
            """Handle notification responses."""
            if future.done():
                _LOGGER.debug("%s: Notification handler already done", self.name)
                return
            future.set_result(data)

        _LOGGER.debug("%s: Subscribe to notifications", self.name)
        await client.start_notify(self._read_char, _notification_handler)

        _LOGGER.debug("%s: Sending command, %s", self.name, key)
        await client.write_gatt_char(self._write_char, command, False)

        async with async_timeout.timeout(5):
            notify_msg = await future
        _LOGGER.info("%s: Notification received: %s", self.name, notify_msg)

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
    ) -> dict | None:
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

    async def _get_basic_info(self) -> dict | None:
        """Return basic info of device."""
        _data = await self._sendcommand(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data
