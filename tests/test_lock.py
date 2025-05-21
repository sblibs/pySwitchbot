import pytest

from switchbot import SwitchbotModel
from switchbot.devices import lock

from .test_adv_parser import generate_ble_device


def create_device_for_command_testing(model: str):
    ble_device = generate_ble_device("aa:bb:cc:dd:ee:ff", "any")
    return lock.SwitchbotLock(
        ble_device, "ff", "ffffffffffffffffffffffffffffffff", model=model
    )


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.LOCK,
        SwitchbotModel.LOCK_LITE,
        SwitchbotModel.LOCK_PRO,
        SwitchbotModel.LOCK_ULTRA,
    ],
)
def test_lock_init(model: str):
    """Test the initialization of the lock device."""
    device = create_device_for_command_testing(model)
    assert device._model == model


@pytest.mark.parametrize(
    "model",
    [
        SwitchbotModel.AIR_PURIFIER,
    ],
)
def test_lock_init_with_invalid_model(model: str):
    """Test that initializing with an invalid model raises ValueError."""
    with pytest.raises(
        ValueError, match="initializing SwitchbotLock with a non-lock model"
    ):
        create_device_for_command_testing(model)
