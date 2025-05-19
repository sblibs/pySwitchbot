from switchbot.adv_parsers.hub3 import calculate_light_intensity


def test_calculate_light_intensity():
    """Test calculating light intensity from Hub 3 light level."""
    # Test valid inputs
    assert calculate_light_intensity(1) == 0
    assert calculate_light_intensity(2) == 50
    assert calculate_light_intensity(5) == 317
    assert calculate_light_intensity(10) == 1023

    # Test invalid inputs
    assert calculate_light_intensity(0) == 0
