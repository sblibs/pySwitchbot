from switchbot.adv_parsers.hub2 import calculate_light_intensity


def test_calculate_light_intensity():
    """Test calculating light intensity from Hub 2 light level."""
    # Test valid inputs
    assert calculate_light_intensity(1) == 0
    assert calculate_light_intensity(2) == 10
    assert calculate_light_intensity(10) == 90
    assert calculate_light_intensity(15) == 510
    assert calculate_light_intensity(21) == 1091

    # Test invalid inputs
    assert calculate_light_intensity(0) == 0
    assert calculate_light_intensity(22) == 0
    assert calculate_light_intensity(-1) == 0
    assert calculate_light_intensity(3.5) == 0
    assert calculate_light_intensity(None) == 0
