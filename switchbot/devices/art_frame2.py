"""Device handlers for Art Frame 2 and AI Memory Frame."""

import secrets
from typing import Any

from .device import (
    SwitchbotEncryptedDevice,
    SwitchbotOperationError,
    SwitchbotSequenceDevice,
    update_after_operation,
)


class SwitchbotArtFrame2(SwitchbotSequenceDevice, SwitchbotEncryptedDevice):
    """Handle image frames with 16-bit image indexes."""

    response_flag: bool = True

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Read device settings without downloading the image bitmap."""
        data = await self._get_basic_info()
        if not data or len(data) < 10 or data[0] != 1:
            return None
        return {
            "battery_charging": bool(data[1] & 0x80),
            "battery": data[1] & 0x7F,
            "firmware": data[2] / 10.0,
            "hardware": data[3],
            "display_size": data[4] >> 4,
            "display_mode": (data[4] >> 3) & 1,
            "last_network_status": (data[4] >> 2) & 1,
            "current_image_index": int.from_bytes(data[5:7], "little"),
            "total_num_of_images": int.from_bytes(data[7:9], "little"),
            "orientation": data[9],
        }

    async def _get_image_indexes(self) -> list[int]:
        """Read the complete, packet-ordered user image bitmap."""
        bitmap = bytearray()
        packet = 0
        total_packets = 1
        while packet < total_packets:
            data = await self._send_command(f"570F7B07{packet:02X}")
            if (
                not data
                or len(data) < 4
                or data[0] != 1
                or data[1] == 0
                or data[2] != packet
                or (packet > 0 and data[1] != total_packets)
                or len(bitmap) + len(data) - 3 > 2560
            ):
                raise SwitchbotOperationError("Invalid image bitmap response")
            total_packets = data[1]
            bitmap.extend(data[3:])
            packet += 1
        return [
            byte_index * 8 + bit + 1
            for byte_index, value in enumerate(bitmap)
            for bit in range(8)
            if value & (1 << bit)
        ]

    async def _set_image_id(self, image_id: int) -> bool:
        result = await self._send_command(
            "570F7A02" + image_id.to_bytes(2, "little").hex()
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def next_image(self) -> bool:
        """Display the next stored image."""
        result = await self._send_command("570F7A0701")
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def prev_image(self) -> bool:
        """Display the previous stored image."""
        result = await self._send_command("570F7A0700")
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def random_image(self) -> bool:
        """Display a random stored user image other than the current image."""
        if not (info := await self.get_basic_info()):
            raise SwitchbotOperationError("Failed to retrieve frame settings")
        choices = [
            index
            for index in await self._get_image_indexes()
            if index != info["current_image_index"]
        ]
        if not choices:
            raise RuntimeError("No images available to select from.")
        return await self._set_image_id(secrets.choice(choices))

    @update_after_operation
    async def set_image(self, index: int) -> bool:
        """Select a user image by its zero-based position in the stored list."""
        indexes = await self._get_image_indexes()
        if index < 0 or index >= len(indexes):
            raise ValueError(f"Image index {index} is out of range.")
        return await self._set_image_id(indexes[index])
