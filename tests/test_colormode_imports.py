"""Test ColorMode imports for backward compatibility."""


def test_colormode_import_from_main_module():
    """Test that ColorMode can be imported from the main switchbot module."""
    from switchbot import ColorMode  # noqa: PLC0415

    # Verify it's the enum we expect
    assert hasattr(ColorMode, "OFF")
    assert hasattr(ColorMode, "COLOR_TEMP")
    assert hasattr(ColorMode, "RGB")
    assert hasattr(ColorMode, "EFFECT")

    # Verify the values
    assert ColorMode.OFF.value == 0
    assert ColorMode.COLOR_TEMP.value == 1
    assert ColorMode.RGB.value == 2
    assert ColorMode.EFFECT.value == 3


def test_colormode_import_from_device_module():
    """Test that ColorMode can be imported from switchbot.devices.device for backward compatibility."""
    from switchbot.devices.device import ColorMode  # noqa: PLC0415

    # Verify it's the enum we expect
    assert hasattr(ColorMode, "OFF")
    assert hasattr(ColorMode, "COLOR_TEMP")
    assert hasattr(ColorMode, "RGB")
    assert hasattr(ColorMode, "EFFECT")

    # Verify the values
    assert ColorMode.OFF.value == 0
    assert ColorMode.COLOR_TEMP.value == 1
    assert ColorMode.RGB.value == 2
    assert ColorMode.EFFECT.value == 3


def test_colormode_import_from_const():
    """Test that ColorMode can be imported from switchbot.const."""
    from switchbot.const import ColorMode  # noqa: PLC0415

    # Verify it's the enum we expect
    assert hasattr(ColorMode, "OFF")
    assert hasattr(ColorMode, "COLOR_TEMP")
    assert hasattr(ColorMode, "RGB")
    assert hasattr(ColorMode, "EFFECT")

    # Verify the values
    assert ColorMode.OFF.value == 0
    assert ColorMode.COLOR_TEMP.value == 1
    assert ColorMode.RGB.value == 2
    assert ColorMode.EFFECT.value == 3


def test_colormode_import_from_const_light():
    """Test that ColorMode can be imported from switchbot.const.light."""
    from switchbot.const.light import ColorMode  # noqa: PLC0415

    # Verify it's the enum we expect
    assert hasattr(ColorMode, "OFF")
    assert hasattr(ColorMode, "COLOR_TEMP")
    assert hasattr(ColorMode, "RGB")
    assert hasattr(ColorMode, "EFFECT")

    # Verify the values
    assert ColorMode.OFF.value == 0
    assert ColorMode.COLOR_TEMP.value == 1
    assert ColorMode.RGB.value == 2
    assert ColorMode.EFFECT.value == 3


def test_all_colormode_imports_are_same_object():
    """Test that all ColorMode imports reference the same enum object."""
    from switchbot import ColorMode as ColorMode1  # noqa: PLC0415
    from switchbot.const import ColorMode as ColorMode3  # noqa: PLC0415
    from switchbot.const.light import ColorMode as ColorMode4  # noqa: PLC0415
    from switchbot.devices.device import ColorMode as ColorMode2  # noqa: PLC0415

    # They should all be the exact same object
    assert ColorMode1 is ColorMode2
    assert ColorMode2 is ColorMode3
    assert ColorMode3 is ColorMode4

    # And their members should be the same
    assert ColorMode1.OFF is ColorMode2.OFF
    assert ColorMode1.COLOR_TEMP is ColorMode3.COLOR_TEMP
    assert ColorMode1.RGB is ColorMode4.RGB
    assert ColorMode1.EFFECT is ColorMode2.EFFECT
