"""Keypad device handling."""

from __future__ import annotations

from .device import SwitchbotDevice


class SwitchbotKeypad(SwitchbotDevice):
    """
    Representation of a Switchbot Keypad (WoKeypad) device.

    Passive BLE-only — no commands. Battery and attempt_state come from
    advertisement parsing in adv_parsers/keypad.py.
    """

    @property
    def attempt_state(self) -> int | None:
        """Return the last attempt state from advertisement data."""
        return self._get_adv_value("attempt_state")
