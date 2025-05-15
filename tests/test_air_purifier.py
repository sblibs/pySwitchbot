from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotEncryptedDevice, SwitchbotModel
from switchbot.const.air_purifier import AirPurifierMode
from switchbot.devices import air_purifier

from .test_adv_parser import generate_ble_device

common_params = [
    (b"7\x00\x00\x95-\x00", "7"),
    (b"*\x00\x00\x15\x04\x00", "*"),
    (b"+\x00\x00\x15\x04\x00", "+"),
    (b"8\x00\x00\x95-\x00", "8"),
]


def create_device_for_command_testing(
    rawAdvData: bytes, model: str, init_data: dict | None = None
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = air_purifier.SwitchbotAirPurifier(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff"
    )
    device.update_from_advertisement(
        make_advertisement_data(ble_device, rawAdvData, model, init_data)
    )
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(
    ble_device: BLEDevice, rawAdvData: bytes, model: str, init_data: dict | None = None
):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": rawAdvData,
            "data": {
                "isOn": True,
                "mode": "level_3",
                "isAqiValid": False,
                "child_lock": False,
                "speed": 100,
                "aqi_level": "excellent",
                "filter element working time": 405,
                "err_code": 0,
                "sequence_number": 161,
            }
            | init_data,
            "isEncrypted": False,
            "model": model,
            "modelFriendlyName": "Air Purifier",
            "modelName": SwitchbotModel.AIR_PURIFIER,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
@pytest.mark.parametrize(
    "pm25",
    [150],
)
async def test_status_from_proceess_adv(rawAdvData, model, pm25):
    device = create_device_for_command_testing(rawAdvData, model, {"pm25": pm25})
    assert device.get_current_percentage() == 100
    assert device.is_on() is True
    assert device.get_current_aqi_level() == "excellent"
    assert device.get_current_mode() == "level_3"
    assert device.get_current_pm25() == 150


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
async def test_get_basic_info_returns_none_when_no_data(rawAdvData, model):
    device = create_device_for_command_testing(rawAdvData, model)
    device._get_basic_info = AsyncMock(return_value=None)

    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
@pytest.mark.parametrize(
    "mode", ["level_1", "level_2", "level_3", "auto", "pet", "sleep"]
)
async def test_set_preset_mode(rawAdvData, model, mode):
    device = create_device_for_command_testing(rawAdvData, model, {"mode": mode})
    await device.set_preset_mode(mode)
    assert device.get_current_mode() == mode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
async def test_turn_on(rawAdvData, model):
    device = create_device_for_command_testing(rawAdvData, model, {"isOn": True})
    await device.turn_on()
    assert device.is_on() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
async def test_turn_off(rawAdvData, model):
    device = create_device_for_command_testing(rawAdvData, model, {"isOn": False})
    await device.turn_off()
    assert device.is_on() is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (b"\x00", None),
        (b"\x07", None),
        (b"\x01\x02\x03", b"\x01\x02\x03"),
    ],
)
async def test__get_basic_info(rawAdvData, model, response, expected):
    device = create_device_for_command_testing(rawAdvData, model)
    device._send_command = AsyncMock(return_value=response)
    result = await device._get_basic_info()
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rawAdvData", "model"),
    common_params,
)
@pytest.mark.parametrize(
    ("basic_info", "result"),
    [
        (
            bytearray(
                b"\x01\xa7\xe9\x8c\x08\x00\xb2\x01\x96\x00\x00\x00\xf0\x00\x00\x17"
            ),
            [True, 2, "level_2", True, False, "excellent", 50, 240, 2.3],
        ),
        (
            bytearray(
                b"\x01\xa8\xec\x8c\x08\x00\xb2\x01\x96\x00\x00\x00\xf0\x00\x00\x17"
            ),
            [True, 2, "pet", True, False, "excellent", 50, 240, 2.3],
        ),
    ],
)
async def test_get_basic_info(rawAdvData, model, basic_info, result):
    device = create_device_for_command_testing(rawAdvData, model)

    async def mock_get_basic_info():
        return basic_info

    device._get_basic_info = AsyncMock(side_effect=mock_get_basic_info)

    info = await device.get_basic_info()
    assert info["isOn"] == result[0]
    assert info["version_info"] == result[1]
    assert info["mode"] == result[2]
    assert info["isAqiValid"] == result[3]
    assert info["child_lock"] == result[4]
    assert info["aqi_level"] == result[5]
    assert info["speed"] == result[6]
    assert info["pm25"] == result[7]
    assert info["firmware"] == result[8]


@pytest.mark.asyncio
@patch.object(SwitchbotEncryptedDevice, "verify_encryption_key", new_callable=AsyncMock)
async def test_verify_encryption_key(mock_parent_verify):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    key_id = "ff"
    encryption_key = "ffffffffffffffffffffffffffffffff"

    mock_parent_verify.return_value = True

    result = await air_purifier.SwitchbotAirPurifier.verify_encryption_key(
        device=ble_device,
        key_id=key_id,
        encryption_key=encryption_key,
    )

    mock_parent_verify.assert_awaited_once_with(
        ble_device,
        key_id,
        encryption_key,
        SwitchbotModel.AIR_PURIFIER,
    )

    assert result is True


def test_get_modes():
    assert AirPurifierMode.get_modes() == [
        "level_1",
        "level_2",
        "level_3",
        "auto",
        "sleep",
        "pet",
    ]
