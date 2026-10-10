import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, call

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from switchbot import (
    MeterProWeatherIcon,
    SwitchbotDevice,
    SwitchbotMeterProCO2,
    SwitchbotOperationError,
)
from switchbot.adv_parsers._sensor_th import decode_temp_humidity
from switchbot.devices.meter_pro import _encode_weather_temperature

READ = "570f6906"
BASELINE = bytes.fromhex("01003292b5008000008000000080000000")


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [(tenths / 10, tenths / 10) for tenths in range(-9, 10)]
    + [
        (19.3, 19.3),
        (-11.7, -11.7),
        (127.9, 127.9),
        (-127.9, -127.9),
        (18.25, 18.3),
        (-18.25, -18.3),
        (0.04, 0.0),
        (-0.04, 0.0),
    ],
)
def test_temperature_round_trip_with_sensor_decoder(temperature, expected):
    encoded = _encode_weather_temperature(temperature)
    assert len(encoded) == 2
    assert encoded[0] <= 9
    assert bool(encoded[1] & 0x80) == (expected >= 0)
    decoded = decode_temp_humidity(encoded + bytes((53,)), None)
    assert decoded["temperature"] == expected
    assert decoded["humidity"] == 53


@pytest.mark.parametrize(
    ("temperature", "expected_bytes"),
    [(0.5, "0580"), (-0.5, "0500"), (0, "0080")],
)
def test_sub_degree_temperature_sign_bytes(temperature, expected_bytes):
    assert _encode_weather_temperature(temperature).hex() == expected_bytes


def create_device():
    device = SwitchbotMeterProCO2(BLEDevice("aa:bb:cc:dd:ee:ff", "meter", {}))
    device._send_command = AsyncMock(return_value=BASELINE)
    device._send_command_locked_with_retry = AsyncMock()
    return device


def configure_write(device, icon=1, network=BASELINE[2:5]):
    if isinstance(icon, MeterProWeatherIcon):
        icon = icon.value
    after = bytes((1, icon)) + network + BASELINE[5:]
    device._send_command_locked_with_retry.side_effect = [BASELINE, b"\x01", after]
    return after


def sent_keys(device):
    return [
        entry.args[0] for entry in device._send_command_locked_with_retry.call_args_list
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response", [BASELINE, BASELINE[:5], BASELINE[:5] + b"\xff", BASELINE + b"\xff"]
)
async def test_get_weather(response):
    device = create_device()
    device._send_command.return_value = response
    state = await device.get_weather()
    assert state == {
        "icon": MeterProWeatherIcon.NONE,
        "temperature_c": 18.2,
        "humidity": 53,
        "fahrenheit_display": True,
    }
    device._send_command.assert_awaited_once_with(READ)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        None,
        b"",
        b"\x00",
        b"\x01",
        bytes.fromhex("01008000"),
        bytes.fromhex("0108008000"),
        bytes.fromhex("01000a8000"),
        bytes.fromhex("0100008064"),
    ],
)
async def test_bad_weather_response(response):
    device = create_device()
    device._send_command.return_value = response
    with pytest.raises(SwitchbotOperationError):
        await device.get_weather()


@pytest.mark.asyncio
@pytest.mark.parametrize("icon", list(MeterProWeatherIcon))
async def test_set_icon_preserves_network(icon):
    device = create_device()
    configure_write(device, icon)
    assert await device.set_weather(icon) is None
    payload = f"570f680601{icon.value:02x}3292b5"
    assert len(bytes.fromhex(payload)) == 9
    assert sent_keys(device) == [READ, payload, READ]
    assert device._send_command_locked_with_retry.call_args_list == [
        call(key, bytearray.fromhex(key), retry, retry + 1)
        for key, retry in [
            (READ, device._retry_count),
            (payload, 0),
            (READ, device._retry_count),
        ]
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("temperature", "humidity", "encoded"),
    [
        (18.2, 53, "3292b5"),
        (-11.7, 57, "370bb9"),
        (-0.5, 1, "350081"),
        (0.5, 1, "358081"),
        (0, 99, "3080e3"),
        (127.9, 99, "39ffe3"),
        (-127.9, 1, "397f81"),
        (18.25, 53.5, "3392b6"),
        (Decimal("18.25"), Decimal("53.5"), "3392b6"),
    ],
)
async def test_explicit_values_preserve_flags(temperature, humidity, encoded):
    device = create_device()
    configure_write(device, network=bytes.fromhex(encoded))
    result = await device.set_weather(
        MeterProWeatherIcon.SUNNY, temperature_c=temperature, humidity=humidity
    )
    assert result is None
    assert sent_keys(device) == [READ, "570f68060101" + encoded, READ]


@pytest.mark.asyncio
@pytest.mark.parametrize("icon", [-1, 8, True, "sunny", 1.0])
async def test_invalid_icon_before_io(icon):
    device = create_device()
    with pytest.raises(
        SwitchbotOperationError, match=r"Weather icon|MeterProWeatherIcon"
    ):
        await device.set_weather(icon)
    device._send_command_locked_with_retry.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("temperature", "humidity"),
    [
        (128, 53),
        (-128, 53),
        (0, 0),
        (0, 100),
        (float("nan"), 53),
        (float("inf"), 53),
        (0, float("nan")),
        (True, 53),
        (0, False),
        ("invalid", 53),
        ("18.2", 53),
        (18.2, "53"),
        (object(), 53),
        (18.2, object()),
        (float("nan"), None),
        (None, 100),
        (Decimal("NaN"), 53),
        (18.2, Decimal("Infinity")),
    ],
)
async def test_invalid_values_before_io(temperature, humidity):
    device = create_device()
    with pytest.raises(
        SwitchbotOperationError, match=r"Temperature|temperature|humidity"
    ):
        await device.set_weather(
            MeterProWeatherIcon.SUNNY, temperature_c=temperature, humidity=humidity
        )
    device._send_command_locked_with_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_fields_rejected_before_io():
    device = create_device()
    with pytest.raises(
        SwitchbotOperationError, match="Supply at least one weather field"
    ):
        await device.set_weather()
    device._send_command_locked_with_retry.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_icon", "network"),
    [
        ({"temperature_c": -11.7}, 0, "370bb5"),
        ({"humidity": 57}, 0, "3292b9"),
        ({"temperature_c": -11.7, "humidity": 57}, 0, "370bb9"),
        ({"icon": MeterProWeatherIcon.SUNNY, "temperature_c": -11.7}, 1, "370bb5"),
        ({"icon": MeterProWeatherIcon.SUNNY, "humidity": 57}, 1, "3292b9"),
        ({"temperature_c": 0}, 0, "3080b5"),
        ({"icon": MeterProWeatherIcon.NONE, "humidity": 57}, 0, "3292b9"),
    ],
)
async def test_partial_updates(kwargs, expected_icon, network):
    device = create_device()
    configure_write(device, expected_icon, bytes.fromhex(network))
    assert await device.set_weather(**kwargs) is None
    assert sent_keys(device) == [READ, f"570f680601{expected_icon:02x}{network}", READ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "network"),
    [({"temperature_c": -0.5}, "050000"), ({"humidity": 57}, "008039")],
)
async def test_partial_updates_preserve_unavailable_fields(kwargs, network):
    device = create_device()
    before = bytes.fromhex("0106008000")
    after = bytes((1, 6)) + bytes.fromhex(network)
    device._send_command_locked_with_retry.side_effect = [before, b"\x01", after]
    assert await device.set_weather(**kwargs) is None
    assert sent_keys(device) == [READ, "570f68060106" + network, READ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("responses", "count"),
    [
        ([b"\x00"], 1),
        ([BASELINE, b"\x00"], 2),
        ([BASELINE, b"\x01", BASELINE], 3),
        ([BASELINE, b"\x01", bytes.fromhex("01013293b5")], 3),
    ],
)
async def test_failures_do_not_rollback(responses, count):
    device = create_device()
    device._send_command_locked_with_retry.side_effect = responses
    with pytest.raises(SwitchbotOperationError):
        await device.set_weather(MeterProWeatherIcon.SUNNY)
    assert device._send_command_locked_with_retry.await_count == count
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
async def test_write_timeout_does_not_retry():
    device = create_device()
    device._send_command_locked_with_retry.side_effect = [BASELINE, TimeoutError()]
    with pytest.raises(TimeoutError):
        await device.set_weather(MeterProWeatherIcon.SUNNY)
    assert device._send_command_locked_with_retry.await_count == 2
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
@pytest.mark.parametrize("icon", [0, 7])
async def test_integer_icon_supported(icon):
    device = create_device()
    configure_write(device, icon)
    await device.set_weather(icon)
    assert sent_keys(device) == [READ, f"570f680601{icon:02x}3292b5", READ]


@pytest.mark.asyncio
@pytest.mark.parametrize("read_step", ["before", "after"])
async def test_transient_read_failure_retries_without_replaying_write(read_step):
    device = create_device()
    device._send_command_locked_with_retry = (
        SwitchbotDevice._send_command_locked_with_retry.__get__(device)
    )
    after = bytes((1, 1)) + BASELINE[2:]
    if read_step == "before":
        responses = [BleakError("transient read error"), BASELINE, b"\x01", after]
        expected_keys = [READ, READ, "570f680601013292b5", READ]
    else:
        responses = [BASELINE, b"\x01", BleakError("transient read error"), after]
        expected_keys = [READ, "570f680601013292b5", READ, READ]
    device._send_command_locked = AsyncMock(side_effect=responses)
    await device.set_weather(MeterProWeatherIcon.SUNNY)
    assert [
        entry.args[0] for entry in device._send_command_locked.call_args_list
    ] == expected_keys
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
async def test_actual_retry_engine_does_not_replay_failed_write():
    device = create_device()
    device._send_command_locked_with_retry = (
        SwitchbotDevice._send_command_locked_with_retry.__get__(device)
    )
    device._send_command_locked = AsyncMock(
        side_effect=[BASELINE, BleakError("lost write acknowledgement")]
    )
    with pytest.raises(BleakError, match="lost write acknowledgement"):
        await device.set_weather(MeterProWeatherIcon.SUNNY)
    assert [entry.args[0] for entry in device._send_command_locked.call_args_list] == [
        READ,
        "570f680601013292b5",
    ]
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
@pytest.mark.parametrize("read_step", ["before", "after"])
async def test_read_retry_exhaustion_does_not_replay_write(read_step):
    device = create_device()
    device._retry_count = 2
    device._send_command_locked_with_retry = (
        SwitchbotDevice._send_command_locked_with_retry.__get__(device)
    )
    failures = [BleakError("persistent read error") for _ in range(3)]
    prefix = [] if read_step == "before" else [BASELINE, b"\x01"]
    device._send_command_locked = AsyncMock(side_effect=prefix + failures)
    with pytest.raises(BleakError, match="persistent read error"):
        await device.set_weather(MeterProWeatherIcon.SUNNY)
    expected_keys = [] if read_step == "before" else [READ, "570f680601013292b5"]
    expected_keys += [READ] * 3
    assert [
        entry.args[0] for entry in device._send_command_locked.call_args_list
    ] == expected_keys
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
async def test_update_ignores_extra_response_bytes():
    device = create_device()
    before = BASELINE[:5] + b"\x11\x22"
    after = bytes((1, 1)) + BASELINE[2:5] + bytes(range(20))
    device._send_command_locked_with_retry.side_effect = [before, b"\x01", after]
    await device.set_weather(MeterProWeatherIcon.SUNNY)
    assert sent_keys(device) == [READ, "570f680601013292b5", READ]


@pytest.mark.asyncio
async def test_operation_lock_covers_whole_sequence():
    device = create_device()
    configure_write(device)
    original = device._send_command_locked_with_retry

    async def command(*args):
        assert device._operation_lock.locked()
        await asyncio.sleep(0)
        return await original(*args)

    device._send_command_locked_with_retry = command
    await device.set_weather(MeterProWeatherIcon.SUNNY)
    assert original.await_count == 3
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
async def test_cancellation_releases_lock():
    device = create_device()
    started = asyncio.Event()

    async def command(*_args):
        started.set()
        await asyncio.Future()

    device._send_command_locked_with_retry.side_effect = command
    task = asyncio.create_task(device.set_weather(MeterProWeatherIcon.SUNNY))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not device._operation_lock.locked()


@pytest.mark.asyncio
async def test_concurrent_updates_do_not_interleave():
    device = create_device()
    responses = iter(
        [
            BASELINE,
            b"\x01",
            bytes((1, 1)) + BASELINE[2:],
            bytes((1, 1)) + BASELINE[2:],
            b"\x01",
            bytes((1, 2)) + BASELINE[2:],
        ]
    )
    keys = []

    async def command(key, _payload, retry, max_attempts):
        assert device._operation_lock.locked()
        expected_retry = device._retry_count if key == READ else 0
        assert (retry, max_attempts) == (expected_retry, expected_retry + 1)
        keys.append(key)
        await asyncio.sleep(0)
        return next(responses)

    device._send_command_locked_with_retry.side_effect = command
    first, second = await asyncio.gather(
        device.set_weather(MeterProWeatherIcon.SUNNY),
        device.set_weather(MeterProWeatherIcon.PARTLY_CLOUDY),
    )
    assert (first, second) == (None, None)
    assert keys == [READ, "570f680601013292b5", READ, READ, "570f680601023292b5", READ]


@pytest.mark.asyncio
async def test_unavailable_measurements_are_preserved():
    device = create_device()
    before = bytes.fromhex("0100008000")
    device._send_command_locked_with_retry.side_effect = [
        before,
        b"\x01",
        bytes.fromhex("0101008000"),
    ]
    assert await device.set_weather(MeterProWeatherIcon.SUNNY) is None
    assert sent_keys(device) == [READ, "570f68060101008000", READ]
