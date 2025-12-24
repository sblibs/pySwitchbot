from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement
from switchbot.devices.art_frame import COMMAND_SET_IMAGE, SwitchbotArtFrame
from switchbot.devices.device import SwitchbotEncryptedDevice

from . import ART_FRAME_INFO
from .test_adv_parser import AdvTestCase, generate_ble_device


def create_device_for_command_testing(
    adv_info: AdvTestCase,
    init_data: dict | None = None,
) -> SwitchbotArtFrame:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = SwitchbotArtFrame(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=adv_info.modelName
    )
    device.update_from_advertisement(
        make_advertisement_data(ble_device, adv_info, init_data)
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice, adv_info: AdvTestCase, init_data: dict | None = None
) -> SwitchBotAdvertisement:
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": adv_info.service_data,
            "data": adv_info.data | init_data,
            "isEncrypted": False,
            "model": adv_info.model,
            "modelFriendlyName": adv_info.modelFriendlyName,
            "modelName": adv_info.modelName,
        }
        | init_data,
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_get_basic_info_none() -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)
    device._get_basic_info = AsyncMock(return_value=None)

    assert await device.get_basic_info() is None

    with pytest.raises(
        RuntimeError, match=r"Failed to retrieve basic info for current image index."
    ):
        await device._get_current_image_index()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "result"),
    [
        (
            b"\x016\x07\x01\x00\x00\x04\x00\xde\x18\xa5\x00\x00\x00\x00\x00\x00",
            [
                False,
                54,
                0.7,
                1,
                0,
                0,
                0,
                0,
                4,
                [0, 222, 24, 165],
            ],
        ),
    ],
)
async def test_get_basic_info_parsing(
    basic_info: str, result: list[bool | int | float | list[int]]
) -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)
    device._get_basic_info = AsyncMock(return_value=basic_info)

    info = await device.get_basic_info()
    assert info["battery_charging"] == result[0]
    assert info["battery"] == result[1]
    assert info["firmware"] == result[2]
    assert info["hardware"] == result[3]
    assert info["display_size"] == result[4]
    assert info["display_mode"] == result[5]
    assert info["last_network_status"] == result[6]
    assert info["current_image_index"] == result[7]
    assert info["total_num_of_images"] == result[8]
    assert info["all_images_index"] == result[9]

    device._update_parsed_data(info)
    assert device.get_all_images_index() == result[9]
    assert device.get_total_images() == result[8]
    assert device.get_current_image_index() == result[7]


@pytest.mark.asyncio
async def test_select_image_with_single_image() -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)

    with (
        patch.object(device, "get_all_images_index", return_value=[1]),
        pytest.raises(RuntimeError, match=r"No images available to select from."),
    ):
        device._select_image_index(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_index", "all_images_index", "expected_cmd"),
    [
        (100, [1, 100, 150], "150"),
        (150, [1, 100, 150], "1"),
        (1, [1, 100, 150], "100"),
    ],
)
async def test_next_image(
    current_index: int, all_images_index: list[int], expected_cmd: str
) -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)

    with (
        patch.object(device, "get_current_image_index", return_value=current_index),
        patch.object(device, "get_all_images_index", return_value=all_images_index),
    ):
        await device.next_image()
        device._send_command.assert_awaited_with(
            COMMAND_SET_IMAGE.format(f"{int(expected_cmd):02X}")
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_index", "all_images_index", "expected_cmd"),
    [
        (100, [1, 100, 150], "1"),
        (150, [1, 100, 150], "100"),
        (1, [1, 100, 150], "150"),
    ],
)
async def test_prev_image(
    current_index: int, all_images_index: list[int], expected_cmd: str
) -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)

    with (
        patch.object(device, "get_current_image_index", return_value=current_index),
        patch.object(device, "get_all_images_index", return_value=all_images_index),
    ):
        await device.prev_image()
        device._send_command.assert_awaited_with(
            COMMAND_SET_IMAGE.format(f"{int(expected_cmd):02X}")
        )


@pytest.mark.asyncio
async def test_set_image_with_invalid_index() -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)

    with (
        patch.object(device, "get_total_images", return_value=3),
        patch.object(device, "get_all_images_index", return_value=[1, 2, 3]),
        pytest.raises(
            ValueError, match=r"Image index 5 is out of range. Total images: 3."
        ),
    ):
        await device.set_image(5)


@pytest.mark.asyncio
async def test_set_image_with_valid_index() -> None:
    device = create_device_for_command_testing(ART_FRAME_INFO)

    with (
        patch.object(device, "get_total_images", return_value=3),
        patch.object(device, "get_all_images_index", return_value=[10, 20, 30]),
    ):
        await device.set_image(1)
        device._send_command.assert_awaited_with(COMMAND_SET_IMAGE.format("14"))


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify: AsyncMock) -> None:
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await SwitchbotArtFrame.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
        model=ART_FRAME_INFO.modelName,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        ART_FRAME_INFO.modelName,
    )

    assert result is True
