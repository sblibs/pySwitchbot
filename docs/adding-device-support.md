# Adding support for a new SwitchBot device

Most "please support device X" requests stall for one reason: nobody has
captured the raw Bluetooth data the library needs. This page explains what to
capture and how, so a maintainer (or you) can turn a request into a working
parser.

You do **not** need to write code to help — a good capture attached to an issue
is often the whole blocker.

## What the library needs

pySwitchbot identifies and decodes devices from their BLE **advertisement**:

- **Service data** under one of the SwitchBot service UUIDs
  (`0000fd3d-0000-1000-8000-00805f9b34fb` or
  `00000d00-0000-1000-8000-00805f9b34fb`). The library dispatches on the first
  byte (the "model byte") of this payload — see `SUPPORTED_TYPES` in
  `switchbot/adv_parser.py`.
- **Manufacturer data** keyed by a SwitchBot company ID (`2409`, `741`, or
  `89`). This usually carries the live state (battery, position, on/off, …).

So the minimum useful capture for a _new_ device is:

1. The **raw service-data bytes** (hex), including which service UUID carried
   them.
2. The **raw manufacturer-data bytes** (hex), including the company ID.
3. The BLE advertised **name** and the device's exact **model** (the model code
   on the box / in the app, e.g. `W1234567`).

For features on an _already-supported_ device (a new mode, a new field), the
state lives in a few bits that change between modes — so you need the **same
fields captured in each state** (see "Capturing state changes" below).

## How to capture advertisements

### nRF Connect (easiest, no computer needed)

[nRF Connect for Mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile)
(Android/iOS) shows raw advertisement data:

1. Open the app and **Scan**.
2. Find your SwitchBot (match by the MAC/name, or by toggling the device and
   watching which entry's data changes).
3. Tap it and expand the advertisement. Copy the **Service Data** and
   **Manufacturer Data** rows verbatim — the UUID/company ID _and_ the hex
   bytes.

### From Python, with this library

If you can already scan from a machine running pySwitchbot, the raw bytes are a
few lines away:

```python
import asyncio
from bleak import BleakScanner


async def main():
    def cb(device, adv):
        for uuid, data in adv.service_data.items():
            print("service", uuid, data.hex())
        for cid, data in adv.manufacturer_data.items():
            print("manufacturer", cid, data.hex())
        print("name", adv.local_name, device.address)

    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    await asyncio.sleep(20)
    await scanner.stop()


asyncio.run(main())
```

To check whether the library _already_ understands a device, feed the same
`BLEDevice` + `AdvertisementData` to the public parser:

```python
from switchbot import parse_advertisement_data

print(parse_advertisement_data(device, adv))  # None ⇒ not recognised
```

## Capturing state changes

For a new **mode or field** on a supported device, the discriminator is one or
a few bits. To find it, capture the advertisement **in each state**, then diff:

- Night-light vs normal on a light → capture both.
- Each fan speed / each lock sub-state → capture each.

Note exactly which physical action you took before each capture. A single
capture in one state is rarely enough — the diff is what reveals the bit.

## Connection-level captures (commands, not advertisements)

Some features are not in the advertisement at all — they are commands the app
sends over a GATT connection (lock operations, keypad password management,
schedules, time sync). These need a **connection** capture, not a scan:

- **Android**: enable _Developer options → Bluetooth HCI snoop log_, perform the
  one action in the SwitchBot app, then pull `btsnoop_hci.log` (via a bug report
  or `adb`) and open it in **Wireshark**. Find the `ATT Write` to the SwitchBot
  and copy the written bytes.
- Capture **one isolated action per log** so the relevant write is easy to find.

⚠️ A connection capture can include your device's session keys. Share only the
specific write/notify bytes for the action, not the whole log, unless you have
scrubbed it.

## What to put in the issue

- Device model code and friendly name.
- The raw hex (service data + UUID, manufacturer data + company ID), or the
  relevant GATT write bytes for command features.
- For state/mode features: the bytes in **each** state, labelled.
- The app version and phone OS, if you used a snoop log.

## Currently needed captures

These open requests are each blocked on a specific capture. If you own the
hardware, grabbing the bytes below moves them forward:

| Issue                                                    | Device               | Capture this                                                                                       |
| -------------------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------- |
| [#490](https://github.com/sblibs/pySwitchbot/issues/490) | Ceiling Light / Pro  | Advertisement in **night-light mode** _and_ in normal/color-temp mode (diff reveals the mode bit). |
| [#447](https://github.com/sblibs/pySwitchbot/issues/447) | Keypad Vision        | GATT write for the app's **delete/view password** action (HCI snoop).                              |
| [#439](https://github.com/sblibs/pySwitchbot/issues/439) | Keypad Touch         | Advertisement service data + manufacturer data, so the model can be registered.                    |
| [#416](https://github.com/sblibs/pySwitchbot/issues/416) | Meter Pro (W1079000) | GATT writes for the app's **time-sync** action (HCI snoop).                                        |
| [#345](https://github.com/sblibs/pySwitchbot/issues/345) | Bot                  | Whether schedules are set over **BLE** (HCI snoop of creating a schedule) or only via cloud.       |
