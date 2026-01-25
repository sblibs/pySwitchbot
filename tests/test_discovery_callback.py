from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

import switchbot.discovery as discovery_module
from switchbot.discovery import GetSwitchbotDevices
from switchbot.models import SwitchBotAdvertisement


@dataclass
class _FakeBleakScanner:
    detection_callback: object
    adapter: str

    async def start(self) -> None:
        # detection_callback signature: (device, advertisement_data)
        self.detection_callback(object(), object())
        self.detection_callback(object(), object())

    async def stop(self) -> None:
        return


@pytest.mark.asyncio
async def test_discover_fires_callback_for_each_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[SwitchBotAdvertisement] = []

    # Patch parse_advertisement_data to return a different parsed object per invocation.
    parsed: list[SwitchBotAdvertisement] = [
        SwitchBotAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            data={"model": "c", "modelName": "Curtain", "data": {"position": 10}},
            device=object(),
            rssi=-80,
            active=True,
        ),
        SwitchBotAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            data={"model": "c", "modelName": "Curtain", "data": {"position": 20}},
            device=object(),
            rssi=-70,
            active=True,
        ),
    ]

    def _fake_parse(_device: object, _advertisement_data: object):
        return parsed.pop(0)

    async def _fake_sleep(_seconds: float) -> None:
        return

    def _fake_bleak_scanner(*, detection_callback, adapter: str):
        return _FakeBleakScanner(detection_callback=detection_callback, adapter=adapter)

    monkeypatch.setattr(discovery_module, "parse_advertisement_data", _fake_parse)
    monkeypatch.setattr(discovery_module.asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(discovery_module.bleak, "BleakScanner", _fake_bleak_scanner)

    scanner = GetSwitchbotDevices(callback=calls.append)
    result = await scanner.discover(scan_timeout=60)

    assert len(calls) == 2
    assert calls[0].data["data"]["position"] == 10
    assert calls[1].data["data"]["position"] == 20

    # discover() retains backwards compatibility by still returning accumulated data.
    assert result["aa:bb:cc:dd:ee:ff"].data["data"]["position"] == 20


@pytest.mark.asyncio
async def test_callback_exception_does_not_break_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = SwitchBotAdvertisement(
        address="11:22:33:44:55:66",
        data={"model": "H", "modelName": "Bot", "data": {}},
        device=object(),
        rssi=-50,
        active=True,
    )

    def _fake_parse(_device: object, _advertisement_data: object):
        return adv

    async def _fake_sleep(_seconds: float) -> None:
        return

    def _fake_bleak_scanner(*, detection_callback, adapter: str):
        class _S:
            async def start(self) -> None:
                detection_callback(object(), object())

            async def stop(self) -> None:
                return

        return _S()

    def _boom(_adv: SwitchBotAdvertisement) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(discovery_module, "parse_advertisement_data", _fake_parse)
    monkeypatch.setattr(discovery_module.asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(discovery_module.bleak, "BleakScanner", _fake_bleak_scanner)

    scanner = GetSwitchbotDevices(callback=_boom)
    result = await scanner.discover(scan_timeout=1)

    assert result["11:22:33:44:55:66"] == adv


@pytest.mark.asyncio
async def test_callback_exception_is_logged_and_suppressed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test that exceptions raised in the user callback are caught,
    logged, and do not crash the discovery process.
    """
    mock_callback = MagicMock(side_effect=RuntimeError("Boom!"))

    scanner = GetSwitchbotDevices(callback=mock_callback)

    adv = SwitchBotAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        data={"model": "H", "modelName": "Bot", "data": {}},
        device=MagicMock(),
        rssi=-80,
        active=True,
    )

    with patch("switchbot.discovery.parse_advertisement_data", return_value=adv):
        scanner.detection_callback(MagicMock(), MagicMock())

    mock_callback.assert_called_once()

    assert "Error in discovery callback" in caplog.text
    assert "Boom!" in caplog.text  # Exception message should also be in the log
