import pytest

from switchbot import SwitchbotModel, parse_advertisement_data

from .test_adv_parser import generate_advertisement_data, generate_ble_device


@pytest.mark.parametrize("pairing", [False, True])
@pytest.mark.parametrize("light_level", [1, 15, 16, 20])
@pytest.mark.parametrize("sensor_inserted", [False, True])
@pytest.mark.parametrize("motion", [False, True])
def test_hub4_advertisement(pairing, light_level, sensor_inserted, motion):
    service = bytes([0, 0, 100, int(pairing), 0x12, 0x82, 0x48])
    manufacturer = bytearray.fromhex("01020304050601ff000000008003993480")
    manufacturer[12] = 0x80 | (0 if sensor_inserted else 0x20) | light_level
    manufacturer[16] = 0x80 if motion else 0
    result = parse_advertisement_data(
        generate_ble_device("01:02:03:04:05:06", "Hub4"),
        generate_advertisement_data(
            manufacturer_data={2409: bytes(manufacturer)},
            service_data={"0000fd3d-0000-1000-8000-00805f9b34fb": service},
        ),
    )
    assert result is not None
    assert result.data["modelName"] is SwitchbotModel.HUB4
    assert result.data["modelFriendlyName"] == "Hub4"
    assert result.data["model"] == service[3:]
    assert result.data["data"] == {
        "sequence_number": 1,
        "network_state": 2,
        "sensor_inserted": sensor_inserted,
        "lightLevel": light_level,
        "temperature_alarm": False,
        "humidity_alarm": False,
        "temp": {"c": 25.3, "f": 77.5},
        "temperature": 25.3,
        "humidity": 52,
        "motion_detected": motion,
    }


@pytest.mark.parametrize("manufacturer", [None, b"", bytes(16)])
def test_hub4_short_manufacturer_data(manufacturer):
    result = parse_advertisement_data(
        generate_ble_device("01:02:03:04:05:06", "Hub4"),
        generate_advertisement_data(
            manufacturer_data={2409: manufacturer},
            service_data={
                "0000fd3d-0000-1000-8000-00805f9b34fb": bytes.fromhex("00006400128248")
            },
        ),
    )
    assert result.data["data"] == {}


def test_hub4_passive_advertisement():
    result = parse_advertisement_data(
        generate_ble_device("01:02:03:04:05:06", "Hub4"),
        generate_advertisement_data(
            manufacturer_data={
                2409: bytes.fromhex("01020304050601ff000000009493193480")
            },
        ),
        SwitchbotModel.HUB4,
    )
    assert result.data["modelName"] is SwitchbotModel.HUB4
    assert result.data["data"]["lightLevel"] == 20
    assert result.data["data"]["temperature"] == -25.3
    assert result.data["data"]["temperature_alarm"] is True
    assert result.data["data"]["humidity_alarm"] is True
    assert "illuminance" not in result.data["data"]
    assert result.active is False
