"""Device handler for the Art Frame."""

import logging
from typing import Any

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)

COMMAND_SET_IMAGE = "570F7A02{}"


class SwitchbotArtFrame(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Representation of a Switchbot Art Frame."""

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.ART_FRAME,
        **kwargs: Any,
    ) -> None:
        super().__init__(device, key_id, encryption_key, model, interface, **kwargs)
        self.response_flag = True

    @classmethod
    async def verify_encryption_key(
        cls,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        model: SwitchbotModel = SwitchbotModel.ART_FRAME,
        **kwargs: Any,
    ) -> bool:
        return await super().verify_encryption_key(
            device, key_id, encryption_key, model, **kwargs
        )

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        _LOGGER.debug("basic info data: %s", _data.hex())

        battery_charging = bool(_data[1] & 0x80)
        battery = _data[1] & 0x7F
        firmware = _data[2] / 10.0
        hardware = _data[3]
        display_size = (_data[4] >> 4) & 0x0F
        display_mode = (_data[4] >> 3) & 0x01
        last_network_status = (_data[4] >> 2) & 0x01
        current_image_index = _data[5]
        total_num_of_images = _data[6]
        all_images_index = [_data[x] for x in range(7, 7 + total_num_of_images)]

        basic_info = {
            "battery_charging": battery_charging,
            "battery": battery,
            "firmware": firmware,
            "hardware": hardware,
            "display_size": display_size,
            "display_mode": display_mode,
            "last_network_status": last_network_status,
            "current_image_index": current_image_index,
            "total_num_of_images": total_num_of_images,
            "all_images_index": all_images_index,
        }
        _LOGGER.debug("Art Frame %s basic info: %s", self._device.address, basic_info)
        return basic_info

    def _select_image_index(self, offset: int) -> int:
        """Select the image index based on the current index and offset."""
        current_index = self.get_current_image_index()
        all_images_index = self.get_all_images_index()

        if not all_images_index or len(all_images_index) <= 1:
            raise RuntimeError("No images available to select from.")

        new_position = (all_images_index.index(current_index) + offset) % len(
            all_images_index
        )
        return all_images_index[new_position]

    async def _get_current_image_index(self) -> None:
        """Validate the current image index."""
        if not await self.get_basic_info():
            raise RuntimeError("Failed to retrieve basic info for current image index.")

    @update_after_operation
    async def next_image(self) -> bool:
        """Display the next image."""
        await self._get_current_image_index()
        idx = self._select_image_index(1)
        result = await self._send_command(COMMAND_SET_IMAGE.format(f"{idx:02X}"))
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def prev_image(self) -> bool:
        """Display the previous image."""
        await self._get_current_image_index()
        idx = self._select_image_index(-1)
        result = await self._send_command(COMMAND_SET_IMAGE.format(f"{idx:02X}"))
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_image(self, index: int) -> bool:
        """Set the image by index."""
        await self._get_current_image_index()
        total_images = self.get_total_images()

        if index < 0 or index >= total_images:
            raise ValueError(
                f"Image index {index} is out of range. Total images: {total_images}."
            )

        all_images_index = self.get_all_images_index()
        img_index = all_images_index[index]
        result = await self._send_command(COMMAND_SET_IMAGE.format(f"{img_index:02X}"))
        return self._check_command_result(result, 0, {1})

    def get_all_images_index(self) -> list[int] | None:
        """Return cached list of all image indexes."""
        return self._get_adv_value("all_images_index")

    def get_current_image_index(self) -> int | None:
        """Return cached current image index."""
        return self._get_adv_value("current_image_index")

    def get_total_images(self) -> int | None:
        """Return cached total number of images."""
        return self._get_adv_value("total_num_of_images")
