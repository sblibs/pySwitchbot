from unittest.mock import AsyncMock, Mock

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel, parse_advertisement_data
from switchbot.devices import curtain
from switchbot.devices.base_cover import COVER_EXT_SUM_KEY

from .test_adv_parser import generate_advertisement_data, generate_ble_device


def create_device_for_command_testing(calibration=True, reverse_mode=False):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 50, calibration)
    )
    curtain_device._send_multiple_commands = AsyncMock()
    curtain_device.update = AsyncMock()
    return curtain_device


def make_advertisement_data(
    ble_device: BLEDevice, in_motion: bool, position: int, calibration: bool = True
):
    """Set advertisement data with defaults."""
    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"c\xc0X\x00\x11\x04",
            "data": {
                "calibration": calibration,
                "battery": 88,
                "inMotion": in_motion,
                "position": position,
                "lightLevel": 1,
                "deviceChain": 1,
            },
            "isEncrypted": False,
            "model": "c",
            "modelFriendlyName": "Curtain",
            "modelName": SwitchbotModel.CURTAIN,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_not_in_motion(reverse_mode):
    """Test passive not in motion advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 0)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening(reverse_mode):
    """Test passive opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 10)
    )

    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing(reverse_mode):
    """Test passive closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_opening_then_stop(reverse_mode):
    """Test passive stopped after opening advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 10)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 10)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_device_passive_closing_then_stop(reverse_mode):
    """Test passive stopped after closing advertisement."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 90)
    )
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 90)
    )

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_not_in_motion(reverse_mode):
    """Test active not in motion."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, False, 0)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 0, 100, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_opening(reverse_mode):
    """Test active opening."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 10, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_closing(reverse_mode):
    """Test active closing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 90, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_opening_then_stop(reverse_mode):
    """Test active stopped after opening."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 10, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    basic_info = bytes([0, 0, 0, 0, 0, 0, 10, 0])

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse_mode", [(True), (False)])
async def test_device_active_closing_then_stop(reverse_mode):
    """Test active stopped after closing."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=reverse_mode)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 100)
    )

    basic_info = bytes([0, 0, 0, 0, 0, 67, 90, 0])

    async def custom_implementation():
        return basic_info

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    await curtain_device.get_basic_info()

    basic_info = bytes([0, 0, 0, 0, 0, 0, 90, 0])

    await curtain_device.get_basic_info()

    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False


@pytest.mark.asyncio
async def test_get_basic_info_returns_none_when_no_data():
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )
    curtain_device._get_basic_info = AsyncMock(return_value=None)

    assert await curtain_device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "result"),
    [
        (
            bytes([0, 1, 10, 2, 255, 255, 50, 4]),
            [1, 1, 2, "right_to_left", 1, 1, 50, 4],
        ),
        (bytes([0, 1, 10, 2, 0, 0, 50, 4]), [1, 1, 2, "left_to_right", 0, 0, 50, 4]),
    ],
)
async def test_get_basic_info(data, result):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device)
    curtain_device.update_from_advertisement(
        make_advertisement_data(ble_device, True, 0)
    )

    async def custom_implementation():
        return data

    curtain_device._get_basic_info = Mock(side_effect=custom_implementation)

    info = await curtain_device.get_basic_info()
    assert info["battery"] == result[0]
    assert info["firmware"] == result[1]
    assert info["chainLength"] == result[2]
    assert info["openDirection"] == result[3]
    assert info["touchToOpen"] == result[4]
    assert info["light"] == result[4]
    assert info["fault"] == result[4]
    assert info["solarPanel"] == result[5]
    assert info["calibration"] == result[5]
    assert info["calibrated"] == result[5]
    assert info["inMotion"] == result[5]
    assert info["position"] == result[6]
    assert info["timers"] == result[7]


@pytest.mark.asyncio
async def test_open():
    curtain_device = create_device_for_command_testing()
    await curtain_device.open()
    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False
    curtain_device._send_multiple_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_close():
    curtain_device = create_device_for_command_testing()
    await curtain_device.close()
    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True
    curtain_device._send_multiple_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop():
    curtain_device = create_device_for_command_testing()
    await curtain_device.stop()
    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is False
    curtain_device._send_multiple_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_position_opening():
    curtain_device = create_device_for_command_testing()
    await curtain_device.set_position(100)
    assert curtain_device.is_opening() is True
    assert curtain_device.is_closing() is False
    curtain_device._send_multiple_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_position_closing():
    curtain_device = create_device_for_command_testing()
    await curtain_device.set_position(0)
    assert curtain_device.is_opening() is False
    assert curtain_device.is_closing() is True
    curtain_device._send_multiple_commands.assert_awaited_once()


def test_get_position():
    curtain_device = create_device_for_command_testing()
    assert curtain_device.get_position() == 50


@pytest.mark.asyncio
async def test_get_extended_info_summary_sends_command():
    curtain_device = create_device_for_command_testing()
    curtain_device._send_command = AsyncMock()
    await curtain_device.get_extended_info_summary()
    curtain_device._send_command.assert_awaited_once_with(key=COVER_EXT_SUM_KEY)


@pytest.mark.asyncio
@pytest.mark.parametrize("data_value", [(None), (b"\x07"), (b"\x00")])
async def test_get_extended_info_summary_returns_none_when_bad_data(data_value):
    curtain_device = create_device_for_command_testing()
    curtain_device._send_command = AsyncMock(return_value=data_value)
    assert await curtain_device.get_extended_info_summary() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "result"),
    [
        ([0, 0, 0], [True, False, False, "right_to_left"]),
        ([255, 255, 0], [False, True, True, "left_to_right"]),
    ],
)
async def test_get_extended_info_summary_returns_device0(data, result):
    curtain_device = create_device_for_command_testing()
    curtain_device._send_command = AsyncMock(return_value=bytes(data))
    ext_result = await curtain_device.get_extended_info_summary()
    assert ext_result["device0"]["openDirectionDefault"] == result[0]
    assert ext_result["device0"]["touchToOpen"] == result[1]
    assert ext_result["device0"]["light"] == result[2]
    assert ext_result["device0"]["openDirection"] == result[3]
    assert "device1" not in ext_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "result"),
    [
        ([0, 0, 1], [True, False, False, "right_to_left"]),
        ([255, 255, 255], [False, True, True, "left_to_right"]),
    ],
)
async def test_get_extended_info_summary_returns_device1(data, result):
    curtain_device = create_device_for_command_testing()
    curtain_device._send_command = AsyncMock(return_value=bytes(data))
    ext_result = await curtain_device.get_extended_info_summary()
    assert ext_result["device1"]["openDirectionDefault"] == result[0]
    assert ext_result["device1"]["touchToOpen"] == result[1]
    assert ext_result["device1"]["light"] == result[2]
    assert ext_result["device1"]["openDirection"] == result[3]


def test_get_light_level():
    curtain_device = create_device_for_command_testing()
    assert curtain_device.get_light_level() == 1


@pytest.mark.parametrize("reverse_mode", [(True), (False)])
def test_is_reversed(reverse_mode):
    curtain_device = create_device_for_command_testing(reverse_mode=reverse_mode)
    assert curtain_device.is_reversed() == reverse_mode


@pytest.mark.parametrize("calibration", [(True), (False)])
def test_is_calibrated(calibration):
    curtain_device = create_device_for_command_testing(calibration=calibration)
    assert curtain_device.is_calibrated() == calibration


def parse_curtain_advertisement(
    ble_device: BLEDevice, mfr_data: bytes, service_data: bytes | None = None
) -> SwitchBotAdvertisement:
    """Parse an advertisement with the Curtain model as fallback."""
    adv_data = generate_advertisement_data(
        manufacturer_data={2409: mfr_data},
        service_data=(
            {"0000fd3d-0000-1000-8000-00805f9b34fb": service_data}
            if service_data
            else {}
        ),
        rssi=-80,
    )
    return parse_advertisement_data(ble_device, adv_data, SwitchbotModel.CURTAIN)


CURTAIN3_PASSIVE_MFR_DATA = b"\xaa\xbb\xcc\xdd\xee\xff\x07\x03S\x11\x04\x01d"
CURTAIN3_ACTIVE_MFR_DATA = b"\xcf;Zwu\x0c\x19\x0b\x00\x11D\x006"
CURTAIN3_SERVICE_DATA = b"{\xc06\x00\x11D"


def test_service_data_replaces_fallback_model():
    """Test a Curtain 3 first seen without service data is identified later."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device)
    curtain_device.update_from_advertisement(
        parse_curtain_advertisement(ble_device, CURTAIN3_PASSIVE_MFR_DATA)
    )
    assert curtain_device.data["model"] == "c"
    assert curtain_device.data["modelFriendlyName"] == "Curtain"

    active = parse_curtain_advertisement(
        ble_device, CURTAIN3_ACTIVE_MFR_DATA, CURTAIN3_SERVICE_DATA
    )
    assert curtain_device.advertisement_changed(active) is True
    curtain_device.update_from_advertisement(active)

    assert curtain_device.data == active.data
    assert curtain_device.data["model"] == "{"
    assert curtain_device.data["modelName"] == SwitchbotModel.CURTAIN_3
    assert curtain_device.data["modelFriendlyName"] == "Curtain 3"
    assert curtain_device.get_position() == 100
    assert curtain_device.is_calibrated() is True

    curtain_device.update_from_advertisement(
        parse_curtain_advertisement(ble_device, CURTAIN3_PASSIVE_MFR_DATA)
    )

    assert curtain_device.data["model"] == "{"
    assert curtain_device.data["modelName"] == SwitchbotModel.CURTAIN_3
    assert curtain_device.data["modelFriendlyName"] == "Curtain 3"
    assert curtain_device.data["rawAdvData"] == CURTAIN3_SERVICE_DATA
    assert curtain_device.get_position() == 17
    assert curtain_device.get_battery_percent() == 100
    assert curtain_device.is_calibrated() is True


def test_service_data_with_same_model_keeps_stored_advertisement():
    """Test the stored advertisement is only merged when the model matches."""
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    curtain_device = curtain.SwitchbotCurtain(ble_device)
    passive = parse_curtain_advertisement(
        ble_device, b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04"
    )
    curtain_device.update_from_advertisement(passive)
    curtain_device.update_from_advertisement(
        parse_curtain_advertisement(
            ble_device,
            b"\xe7\xabF\xac\x8f\x92|\x0f\x00\x11\x04",
            b"c\xc0X\x00\x11\x04",
        )
    )

    assert curtain_device.data == passive.data | {
        "data": passive.data["data"] | {"calibration": True, "battery": 88}
    }
