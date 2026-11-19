from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from switchbot import SwitchBotAdvertisement, SwitchbotModel
from switchbot.const.light import ColorMode
from switchbot.devices import ceiling_light

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(
    init_data: dict | None = None, model: SwitchbotModel = SwitchbotModel.CEILING_LIGHT
):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    device = ceiling_light.SwitchbotCeilingLight(ble_device, model=model)
    device.update_from_advertisement(make_advertisement_data(ble_device, init_data))
    device._send_command = AsyncMock()
    device._check_command_result = MagicMock()
    device.update = AsyncMock()
    return device


def make_advertisement_data(ble_device: BLEDevice, init_data: dict | None = None):
    """Set advertisement data with defaults."""
    if init_data is None:
        init_data = {}

    return SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={
            "rawAdvData": b"q\x00",
            "data": {
                "brightness": 1,
                "color_mode": 1,
                "cw": 6387,
                "isOn": False,
                "sequence_number": 10,
            }
            | init_data,
            "isEncrypted": False,
            "model": b"q\x00",
            "modelFriendlyName": "Ceiling Light",
            "modelName": SwitchbotModel.CEILING_LIGHT,
        },
        device=ble_device,
        rssi=-80,
        active=True,
    )


@pytest.mark.asyncio
async def test_default_info():
    """Test default initialization of the ceiling light."""
    device = create_device_for_command_testing()

    assert device.rgb is None

    device._state = {"cw": 3200}

    assert device.is_on() is False
    assert device.on is False
    assert device.color_mode == ColorMode.COLOR_TEMP
    assert device.color_modes == {ColorMode.COLOR_TEMP}
    assert device.color_temp == 3200
    assert device.brightness == 1
    assert device.min_temp == 2700
    assert device.max_temp == 6500
    assert device.get_effect_list is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("basic_info", "version_info"), [(True, False), (False, True), (False, False)]
)
async def test_get_basic_info_returns_none(basic_info, version_info):
    device = create_device_for_command_testing()
    device._send_command = AsyncMock(side_effect=[version_info, basic_info])
    device._check_command_result = MagicMock(
        side_effect=[bool(version_info), bool(basic_info)]
    )

    assert await device.get_basic_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("info_data", "result"),
    [
        (
            {
                "basic_info": b"\x01\x80=\x0f\xa1\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [True, 61, 4001, 0, 2.1],
        ),
        (
            {
                "basic_info": b"\x01\x80\x0e\x12B\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [True, 14, 4674, 0, 2.1],
        ),
        (
            {
                "basic_info": b"\x01\x00\x0e\x10\x96\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [False, 14, 4246, 0, 2.1],
        ),
        pytest.param(
            {
                "basic_info": b"\x01\xc0\x0e\x10\x96\x00\x01",
                "version_info": b"\x01d\x15\x0f\x00\x00\x00\x00\x00\x00\x00\n\x00",
            },
            [True, 14, 4246, 1, 2.1],
            id="night-color-mode",
        ),
    ],
)
async def test_get_basic_info(info_data, result):
    """Test getting basic info from the ceiling light."""
    device = create_device_for_command_testing()
    device._send_command = AsyncMock(
        side_effect=[info_data["version_info"], info_data["basic_info"]]
    )
    device._check_command_result = MagicMock(side_effect=[True, True])
    info = await device.get_basic_info()

    assert info["isOn"] is result[0]
    assert info["brightness"] == result[1]
    assert info["cw"] == result[2]
    assert info["color_mode"] == result[3]
    assert info["firmware"] == result[4]
    assert device.is_night_light_on() is bool(result[3])


@pytest.mark.asyncio
async def test_get_basic_info_ignores_invalid_color_temp() -> None:
    """Test retaining the last color temp when basic info reports a placeholder."""
    device = create_device_for_command_testing()
    device._state["cw"] = 3625
    device._send_command = AsyncMock(
        side_effect=[
            b"\x01d\x18\x0e\x00\x00\x00\x00\x00\x00\x00\x0c\x01",
            b"\x01\x80F\xff\x00\x01\x00",
        ]
    )
    device._check_command_result = MagicMock(side_effect=[True, True])

    info = await device.get_basic_info()

    assert info is not None
    assert info["cw"] == 3625
    assert device.color_temp == 3625


@pytest.mark.asyncio
async def test_get_basic_info_uses_default_for_initial_invalid_color_temp() -> None:
    """Test using the default color temp for an initial placeholder."""
    device = create_device_for_command_testing()
    device._send_command = AsyncMock(
        side_effect=[
            b"\x01d\x18\x0e\x00\x00\x00\x00\x00\x00\x00\x0c\x01",
            b"\x01\x80F\xff\x00\x01\x00",
        ]
    )
    device._check_command_result = MagicMock(side_effect=[True, True])

    info = await device.get_basic_info()

    assert info is not None
    assert info["cw"] == 4001
    assert device.color_temp == 4001


@pytest.mark.asyncio
async def test_set_color_temp():
    """Test setting color temperature."""
    device = create_device_for_command_testing()

    await device.set_color_temp(50, 3000)

    device._send_command.assert_called_with(
        device._set_color_temp_command.format("320BB8")
    )


@pytest.mark.asyncio
async def test_turn_on():
    """Test turning on the ceiling light."""
    device = create_device_for_command_testing({"isOn": True})

    await device.turn_on()

    device._send_command.assert_called_with(device._turn_on_command)

    assert device.is_on() is True


@pytest.mark.asyncio
async def test_turn_off():
    """Test turning off the ceiling light."""
    device = create_device_for_command_testing({"isOn": False})

    await device.turn_off()

    device._send_command.assert_called_with(device._turn_off_command)

    assert device.is_on() is False


@pytest.mark.asyncio
async def test_set_night_light_on():
    """Test turning night light mode on."""
    device = create_device_for_command_testing()
    device._state = {"cw": 2700}

    await device.set_night_light(True)

    device._send_command.assert_called_with(
        device._set_night_light_command.format("01", "140A8C")
    )


@pytest.mark.asyncio
async def test_set_night_light_off():
    """Test turning night light mode off."""
    device = create_device_for_command_testing()
    device._state = {"cw": 2700}

    await device.set_night_light(False)

    device._send_command.assert_called_with(
        device._set_night_light_command.format("00", "640A8C")
    )


@pytest.mark.asyncio
async def test_set_night_light_custom_brightness():
    """Test that an explicit brightness overrides the night-light default."""
    device = create_device_for_command_testing()
    device._state = {"cw": 2700}

    await device.set_night_light(True, brightness=30)

    device._send_command.assert_called_with(
        device._set_night_light_command.format("01", "1E0A8C")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("brightness", [-1, 101, 300])
async def test_set_night_light_invalid_brightness(brightness):
    """Test that an out-of-range explicit brightness is rejected."""
    device = create_device_for_command_testing()
    device._state = {"cw": 2700}

    with pytest.raises(ValueError, match="Brightness must be between 0 and 100"):
        await device.set_night_light(True, brightness=brightness)

    device._send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("color_mode", "expected"),
    [
        (0, False),
        (1, True),
        (None, None),
    ],
)
async def test_is_night_light_on(color_mode, expected):
    """Test reading the cached night light state."""
    device = create_device_for_command_testing()
    if color_mode is not None:
        device._state = {"color_mode": color_mode}

    assert device.is_night_light_on() is expected


@pytest.mark.asyncio
async def test_set_brightness():
    """Test setting brightness."""
    device = create_device_for_command_testing()

    await device.set_brightness(75)

    device._send_command.assert_called_with(
        device._set_brightness_command.format("4B0FA1")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adv_value", "expected_color_mode"),
    [
        (0, ColorMode.COLOR_TEMP),
        (1, ColorMode.COLOR_TEMP),
        (4, ColorMode.EFFECT),
        (10, ColorMode.OFF),
        (None, ColorMode.OFF),
    ],
)
async def test_get_color_mode(adv_value, expected_color_mode):
    """Test getting color mode."""
    device = create_device_for_command_testing()

    with patch.object(device, "_get_adv_value", return_value=adv_value):
        assert device.color_mode == expected_color_mode


@pytest.mark.asyncio
async def test_get_color_mode_prefers_cached_state():
    """Test that color_mode prefers the _state cache over the adv value."""
    device = create_device_for_command_testing()
    device._state = {"color_mode": 4}  # MUSIC -> EFFECT

    with patch.object(device, "_get_adv_value", return_value=0):  # COLOR_TEMP
        assert device.color_mode == ColorMode.EFFECT
