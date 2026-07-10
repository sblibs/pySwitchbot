"""Library to handle connection with Switchbot."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, ClassVar

from bleak.backends.device import BLEDevice

from ..const import SwitchbotModel
from ..const.fan import (
    CirculatorFanProMode,
    FanMode,
    HorizontalOscillationAngle,
    NightLightState,
    StandingFanMode,
    VerticalOscillationAngle,
)
from .device import (
    DEVICE_GET_BASIC_SETTINGS_KEY,
    SwitchbotEncryptedDevice,
    SwitchbotSequenceDevice,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)


COMMAND_HEAD = "570f41"
# Circulator Fan (single-axis): start/stop oscillation with V kept unchanged.
# These also serve as the explicit horizontal-only commands since the byte
# layout is identical.
COMMAND_START_OSCILLATION = f"{COMMAND_HEAD}020101ff"
COMMAND_STOP_OSCILLATION = f"{COMMAND_HEAD}020102ff"
COMMAND_START_HORIZONTAL_OSCILLATION = COMMAND_START_OSCILLATION
COMMAND_STOP_HORIZONTAL_OSCILLATION = COMMAND_STOP_OSCILLATION
COMMAND_START_VERTICAL_OSCILLATION = f"{COMMAND_HEAD}0201ff01"  # H keep, V start
COMMAND_STOP_VERTICAL_OSCILLATION = f"{COMMAND_HEAD}0201ff02"  # H keep, V stop
# Standing Fan (dual-axis): start/stop both axes at once.
COMMAND_START_OSCILLATION_ALL_AXES = f"{COMMAND_HEAD}02010101"
COMMAND_STOP_OSCILLATION_ALL_AXES = f"{COMMAND_HEAD}02010202"
COMMAND_SET_OSCILLATION_PARAMS = f"{COMMAND_HEAD}0202"  # +angles
COMMAND_SET_NIGHT_LIGHT = f"{COMMAND_HEAD}0502"  # +state
# Standing Fan (FAN2) extra controls.
COMMAND_SET_DISPLAY_LIGHT = f"{COMMAND_HEAD}0501"  # +state + FFFF (front LED display)
COMMAND_SET_SOUND = f"{COMMAND_HEAD}0601"  # +level (64 on / 00 off)
COMMAND_SET_AUTO_RECENTER = f"{COMMAND_HEAD}0205"  # +both axes (0101 on / 0202 off)
COMMAND_SET_CHILD_LOCK = f"{COMMAND_HEAD}07"  # +state (01 on / 02 off)
COMMAND_SET_MODE = {
    FanMode.NORMAL.name.lower(): f"{COMMAND_HEAD}030101ff",
    FanMode.NATURAL.name.lower(): f"{COMMAND_HEAD}030102ff",
    FanMode.SLEEP.name.lower(): f"{COMMAND_HEAD}030103",
    FanMode.BABY.name.lower(): f"{COMMAND_HEAD}030104",
}
COMMAND_SET_STANDING_FAN_MODE = {
    **COMMAND_SET_MODE,
    StandingFanMode.CUSTOM_NATURAL.name.lower(): f"{COMMAND_HEAD}030105",
}
COMMAND_SET_PERCENTAGE = f"{COMMAND_HEAD}0302"  #  +speed
COMMAND_GET_BASIC_INFO = "570f428102"


class SwitchbotFan(SwitchbotSequenceDevice):
    """Representation of a Switchbot Circulator Fan."""

    _turn_on_command = f"{COMMAND_HEAD}0101"
    _turn_off_command = f"{COMMAND_HEAD}0102"
    _mode_enum: ClassVar[type[Enum]] = FanMode
    _command_set_mode: ClassVar[dict[str, str]] = COMMAND_SET_MODE
    _command_start_oscillation: ClassVar[str] = COMMAND_START_OSCILLATION
    _command_stop_oscillation: ClassVar[str] = COMMAND_STOP_OSCILLATION

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (_data1 := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None

        _LOGGER.debug("data: %s", _data)
        return self._parse_basic_info(_data, _data1)

    def _parse_basic_info(self, _data: bytes, _data1: bytes) -> dict[str, Any]:
        """Decode the basic-info connection response into a state dict."""
        battery = _data[2] & 0b01111111
        isOn = bool(_data[3] & 0b10000000)
        oscillating_horizontal = bool(_data[3] & 0b01000000)
        oscillating_vertical = bool(_data[3] & 0b00100000)
        oscillating = oscillating_horizontal or oscillating_vertical
        _mode = _data[8] & 0b00000111
        mode_enum = self._mode_enum
        max_mode = max(m.value for m in mode_enum)
        mode = mode_enum(_mode).name.lower() if 1 <= _mode <= max_mode else None
        speed = _data[9]
        firmware = _data1[2] / 10.0

        info: dict[str, Any] = {
            "battery": battery,
            "isOn": isOn,
            "oscillating": oscillating,
            "oscillating_horizontal": oscillating_horizontal,
            "oscillating_vertical": oscillating_vertical,
            "mode": mode,
            "speed": speed,
            "firmware": firmware,
        }
        # Night light is only meaningful for models that expose it. Copy from
        # the latest advertisement parse if the parser put it there.
        night_light = self._get_adv_value("nightLight")
        if night_light is not None:
            info["nightLight"] = night_light
        return info

    async def _get_basic_info(self, cmd: str) -> bytes | None:
        """Return basic info of device."""
        _data = await self._send_command(key=cmd, retry=self._retry_count)

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    @update_after_operation
    async def set_preset_mode(self, preset_mode: str) -> bool:
        """Send command to set fan preset_mode."""
        result = await self._send_command(self._command_set_mode[preset_mode])
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_percentage(self, percentage: int) -> bool:
        """Send command to set fan percentage."""
        result = await self._send_command(f"{COMMAND_SET_PERCENTAGE}{percentage:02X}")
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan oscillation"""
        cmd = (
            self._command_start_oscillation
            if oscillating
            else self._command_stop_oscillation
        )
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_horizontal_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan horizontal (left-right) oscillation only."""
        cmd = (
            COMMAND_START_HORIZONTAL_OSCILLATION
            if oscillating
            else COMMAND_STOP_HORIZONTAL_OSCILLATION
        )
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_vertical_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan vertical (up-down) oscillation only."""
        cmd = (
            COMMAND_START_VERTICAL_OSCILLATION
            if oscillating
            else COMMAND_STOP_VERTICAL_OSCILLATION
        )
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    def get_current_percentage(self) -> Any:
        """Return cached percentage."""
        return self._get_adv_value("speed")

    def is_on(self) -> bool | None:
        """Return fan state from cache."""
        return self._get_adv_value("isOn")

    def get_oscillating_state(self) -> Any:
        """Return cached oscillating."""
        return self._get_adv_value("oscillating")

    def get_horizontal_oscillating_state(self) -> Any:
        """Return cached horizontal (left-right) oscillating state."""
        return self._get_adv_value("oscillating_horizontal")

    def get_vertical_oscillating_state(self) -> Any:
        """Return cached vertical (up-down) oscillating state."""
        return self._get_adv_value("oscillating_vertical")

    def get_current_mode(self) -> Any:
        """Return cached mode."""
        return self._get_adv_value("mode")

    @property
    def fan_modes(self) -> list[str]:
        """Return the supported preset (wind) modes for this device."""
        return self._mode_enum.get_modes()


class SwitchbotStandingFan(SwitchbotFan):
    """Representation of a Switchbot Standing Fan (FAN2)."""

    _mode_enum: ClassVar[type[Enum]] = StandingFanMode
    _command_set_mode: ClassVar[dict[str, str]] = COMMAND_SET_STANDING_FAN_MODE
    _command_start_oscillation: ClassVar[str] = COMMAND_START_OSCILLATION_ALL_AXES
    _command_stop_oscillation: ClassVar[str] = COMMAND_STOP_OSCILLATION_ALL_AXES

    def _parse_basic_info(self, _data: bytes, _data1: bytes) -> dict[str, Any]:
        """Add the Standing-Fan-only fields to the basic-info response."""
        info = super()._parse_basic_info(_data, _data1)
        # Sweep angle as the raw device byte: horizontal is the angle in degrees
        # (30/60/90); vertical encodes 90 as 95 (see VerticalOscillationAngle).
        info["oscillating_horizontal_angle"] = _data[4]
        info["oscillating_vertical_angle"] = _data[6]
        info["charging"] = bool(_data[2] & 0b10000000)
        info["child_lock"] = bool(_data[3] & 0b00000001)
        info["display"] = bool(_data[3] & 0b00000010)
        # bit 4 = horizontal axis, bit 3 = vertical; the app toggles both at once.
        info["auto_recenter"] = bool(_data[3] & 0b00011000)
        if len(_data) > 10:
            info["sound"] = bool(_data[10] & 0b01111111)
        return info

    @update_after_operation
    async def set_horizontal_oscillation_angle(
        self, angle: HorizontalOscillationAngle | int
    ) -> bool:
        """Set horizontal oscillation angle (30 / 60 / 90 degrees)."""
        value = HorizontalOscillationAngle(angle).value
        cmd = f"{COMMAND_SET_OSCILLATION_PARAMS}{value:02X}FFFFFF"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_vertical_oscillation_angle(
        self, angle: VerticalOscillationAngle | int
    ) -> bool:
        """
        Set vertical oscillation angle (30 / 60 / 90 degrees).

        The device uses a different byte encoding on the vertical axis than
        on the horizontal one: 90° maps to byte 0x5F (95), not 0x5A (90),
        which the firmware interprets as an axis halt. Use
        `VerticalOscillationAngle` (or the raw byte values 30 / 60 / 95).
        """
        value = VerticalOscillationAngle(angle).value
        cmd = f"{COMMAND_SET_OSCILLATION_PARAMS}FFFF{value:02X}FF"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_night_light(self, state: NightLightState | int) -> bool:
        """Set night-light state (LEVEL_1, LEVEL_2, OFF)."""
        value = NightLightState(state).value
        cmd = f"{COMMAND_SET_NIGHT_LIGHT}{value:02X}FFFF"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_child_lock(self, enabled: bool) -> bool:
        """Enable or disable the child lock."""
        cmd = f"{COMMAND_SET_CHILD_LOCK}{'01' if enabled else '02'}"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_display(self, enabled: bool) -> bool:
        """Turn the front display (LED) on or off."""
        cmd = f"{COMMAND_SET_DISPLAY_LIGHT}{'01' if enabled else '02'}FFFF"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_sound(self, enabled: bool) -> bool:
        """Turn the key tone (buzzer) on or off."""
        cmd = f"{COMMAND_SET_SOUND}{'64' if enabled else '00'}"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_auto_recenter(self, enabled: bool) -> bool:
        """Enable or disable auto return-to-center on both axes."""
        cmd = f"{COMMAND_SET_AUTO_RECENTER}{'0101' if enabled else '0202'}"
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    def get_horizontal_oscillation_angle(self) -> int | None:
        """Return cached horizontal oscillation angle (raw device byte)."""
        return self._get_adv_value("oscillating_horizontal_angle")

    def get_vertical_oscillation_angle(self) -> int | None:
        """Return cached vertical oscillation angle (raw device byte; 90° = 95)."""
        return self._get_adv_value("oscillating_vertical_angle")

    def get_night_light_state(self) -> int | None:
        """Return cached night light state."""
        return self._get_adv_value("nightLight")

    def is_charging(self) -> bool | None:
        """Return cached charging state."""
        return self._get_adv_value("charging")

    def get_child_lock(self) -> bool | None:
        """Return cached child-lock state."""
        return self._get_adv_value("child_lock")

    def get_display(self) -> bool | None:
        """Return cached front-display (LED) state."""
        return self._get_adv_value("display")

    def get_sound(self) -> bool | None:
        """Return cached key-tone (buzzer) state."""
        return self._get_adv_value("sound")

    def get_auto_recenter(self) -> bool | None:
        """Return cached auto-recenter (return-to-center) state."""
        return self._get_adv_value("auto_recenter")


class SwitchbotCirculatorFanPro(SwitchbotEncryptedDevice, SwitchbotFan):
    """
    Representation of a Switchbot Circulator Fan Pro (W1160).

    The Pro uses extended commands (``57 0F <subcmd> …``) with a control-source
    byte (0x29 = Home Assistant), wrapped in the encrypted command shell, so it
    extends SwitchbotEncryptedDevice. Fan power uses subcommand 0x41 (open/close
    sub-op 0x11); the night light uses subcommand 0x96 and supports on/off plus
    a choice between two brightness levels via ``turn_on_light(low=...)``
    (level 1 / bright or level 2 / dim).
    """

    _model = SwitchbotModel.CIRCULATOR_FAN_PRO

    # Fan power: ext 0x0F, subcmd 0x41, 0x11 = 开关机, 0x29 = control source
    # (Home Assistant), byte5 0x01 = on / 0x00 = off / 0x02 = toggle.
    _turn_on_command = "570f41112901"
    _turn_off_command = "570f41112900"
    # Preset mode: the 0x11 power command also carries the running mode in byte6
    # (turning the fan on). The Pro's mode 0x04 is hurricane, not the legacy baby.
    _mode_enum: ClassVar[type[Enum]] = CirculatorFanProMode
    _command_set_mode: ClassVar[dict[str, str]] = {
        mode.name.lower(): f"570f41112901{mode.value:02X}"
        for mode in CirculatorFanProMode
    }
    # Night light: ext 0x0F, subcmd 0x96, byte3 0x0A, byte4 0x02, then a state
    # byte: bit0 = on/off (0 off / 1 on), bit1 = level (0 high / 1 low).
    # off = 0x00, on high = 0x01, on low = 0x03.
    _night_light_command = "570f960a02{}"
    # Oscillation: ext 0x0F, subcmd 0x02, 0x29 = control source (Home Assistant),
    # then per-axis action bytes [horizontal, vertical] where 0x01 = start,
    # 0x02 = stop, 0xFF = keep current. The Pro is dual-axis, so the all-axes
    # start/stop variants toggle both axes at once.
    _command_start_oscillation: ClassVar[str] = "570f4102290101"
    _command_stop_oscillation: ClassVar[str] = "570f4102290202"
    _command_start_horizontal_oscillation: ClassVar[str] = "570f41022901ff"
    _command_stop_horizontal_oscillation: ClassVar[str] = "570f41022902ff"
    _command_start_vertical_oscillation: ClassVar[str] = "570f410229ff01"
    _command_stop_vertical_oscillation: ClassVar[str] = "570f410229ff02"

    def __init__(
        self,
        device: BLEDevice,
        key_id: str,
        encryption_key: str,
        interface: int = 0,
        model: SwitchbotModel = SwitchbotModel.CIRCULATOR_FAN_PRO,
        **kwargs: Any,
    ) -> None:
        """Initialize the Circulator Fan Pro."""
        super().__init__(device, key_id, encryption_key, interface, model, **kwargs)

    async def get_basic_info(self) -> dict[str, Any] | None:
        """
        Get device basic info.

        The Pro carries all runtime state (fan + night light) in its
        advertisement, and its GATT basic-info responses differ from the
        legacy Circulator Fan, so parse only the firmware here and do so
        defensively.
        """
        if not (_data := await self._get_basic_info(COMMAND_GET_BASIC_INFO)):
            return None
        if not (_data1 := await self._get_basic_info(DEVICE_GET_BASIC_SETTINGS_KEY)):
            return None

        _LOGGER.debug(
            "Circulator Fan Pro basic info: data=%s data1=%s",
            _data.hex(),
            _data1.hex(),
        )
        info: dict[str, Any] = {}
        if len(_data1) > 2:
            info["firmware"] = _data1[2] / 10.0
        return info

    @update_after_operation
    async def set_percentage(self, percentage: int) -> bool:
        """
        Set the fan speed (1-100).

        Speed lives in byte7 of the 0x11 power command and only applies in
        direct mode, so this sends "on + direct mode + speed".
        """
        percentage = max(1, min(100, percentage))
        result = await self._send_command(f"570f4111290101{percentage:02X}")
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_horizontal_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan horizontal (left-right) oscillation only."""
        cmd = (
            self._command_start_horizontal_oscillation
            if oscillating
            else self._command_stop_horizontal_oscillation
        )
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def set_vertical_oscillation(self, oscillating: bool) -> bool:
        """Send command to set fan vertical (up-down) oscillation only."""
        cmd = (
            self._command_start_vertical_oscillation
            if oscillating
            else self._command_stop_vertical_oscillation
        )
        result = await self._send_command(cmd)
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_on_light(self, low: bool = False) -> bool:
        """Turn the night light on (low selects level 2 / dim, else level 1 / bright)."""
        state = 0x03 if low else 0x01
        result = await self._send_command(
            self._night_light_command.format(f"{state:02X}")
        )
        return self._check_command_result(result, 0, {1})

    @update_after_operation
    async def turn_off_light(self) -> bool:
        """Turn the night light off."""
        result = await self._send_command(self._night_light_command.format("00"))
        return self._check_command_result(result, 0, {1})

    def is_night_light_on(self) -> bool | None:
        """Return the cached night-light power state."""
        return self._get_adv_value("night_light_is_on")

    def get_night_light_level(self) -> int | None:
        """Return the cached night-light level (1 high, 2 low, 0 off)."""
        return self._get_adv_value("night_light_level")
