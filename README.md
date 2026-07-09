# pySwitchbot [![codecov](https://codecov.io/gh/sblibs/pySwitchbot/graph/badge.svg?token=TI027U5ISQ)](https://codecov.io/gh/sblibs/pySwitchbot)

Library to control Switchbot IoT devices https://www.switch-bot.com/

## Setting up the environment

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Obtaining encryption key for Switchbot Locks

Using the script `scripts/get_encryption_key.py` you can manually obtain locks encryption key.

Usage:

```shell
$ python3 scripts/get_encryption_key.py MAC USERNAME
Key ID: XX
Encryption key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Where `MAC` is MAC address of the lock and `USERNAME` is your SwitchBot account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

### Troubleshooting key retrieval

Key retrieval talks to SwitchBot's account API with your username and
password. The most common failures are account-side, not bugs in this library:

- **`Authentication failed: ...`** — the username/password were rejected. This
  happens when:
  - Two-factor authentication (2FA) is enabled on the account. The API login
    used here does not support a verification code, so 2FA accounts cannot
    retrieve keys this way — temporarily disable 2FA, fetch the key, then
    re-enable it.
  - The account was created via "Sign in with Apple"/Google and has no
    password set. Set a password in the SwitchBot app first, or use an
    email/password account.
  - The username is an email but the account is registered to a phone number
    (or vice versa). Use the exact identifier you log in with.
- **`Failed to retrieve encryption key from SwitchBot Account: ...`** —
  authentication succeeded but the key could not be read. Usually the account
  is not the device **owner**: keys are only returned to the owning account,
  not to shared/family members. Retrieve the key from the owner account, or
  transfer ownership in the app.

The key only needs to be fetched once; store the `key_id` and encryption key
and reuse them — there is no need to call the script on every connection.

## Device discovery and active scanning

SwitchBot devices put their model identifier in the BLE **service data**, which
is only sent in the scan response (`SCAN_RSP`). A scanner must use **active
scanning** to request that response — passive scanning never sees it.

`GetSwitchbotDevices().discover()` uses an active scanner by default, so it
works out of the box. The problem appears when advertisements come from a
_passive_ source instead — for example a Home Assistant adapter or ESPHome
Bluetooth proxy configured for passive-only scanning. In that case the
`service_data` is missing and most models cannot be identified: detection falls
back to manufacturer data, which only resolves a handful of device types. The
typical symptom is "some of my SwitchBot devices are discovered but not all."

If devices are missing, enable active scanning on whatever feeds the
advertisements (the BLE adapter or proxy), then re-scan.

## Examples:

#### WoLock (Lock-Pro)

Unlock:

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock
from switchbot.const import SwitchbotModel

BLE_MAC="XX:XX:XX:XX:XX:XX" # The MAC of your lock
KEY_ID="XX" # The key-ID of your encryption-key for your lock
ENC_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # The encryption-key with key-ID "XX"
LOCK_MODEL=SwitchbotModel.LOCK_PRO # Your lock model (here we use the Lock-Pro)


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(
        wolock[BLE_MAC].device, KEY_ID, ENC_KEY, model=LOCK_MODEL
    ).unlock()


asyncio.run(main())
```

Lock:

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock
from switchbot.const import SwitchbotModel

BLE_MAC="XX:XX:XX:XX:XX:XX" # The MAC of your lock
KEY_ID="XX" # The key-ID of your encryption-key for your lock
ENC_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # The encryption-key with key-ID "XX"
LOCK_MODEL=SwitchbotModel.LOCK_PRO # Your lock model (here we use the Lock-Pro)


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(
        wolock[BLE_MAC].device, KEY_ID, ENC_KEY, model=LOCK_MODEL
    ).lock()


asyncio.run(main())
```

#### WoCurtain (Curtain 3)

```python
import asyncio
from pprint import pprint
from switchbot import GetSwitchbotDevices
from switchbot.devices import curtain


async def main():
    # get the BLE advertisement data of all switchbot devices in the vicinity
    advertisement_data = await GetSwitchbotDevices().discover()

    for i in advertisement_data.values():
        pprint(i)
        print()  # print newline so that devices' data is separated visually

    # find your device's BLE address by inspecting the above printed debug logs, example below
    ble_address = "9915077C-C6FD-5FF6-27D3-45087898790B"
    # get the BLE device (via its address) and construct a curtain device
    ble_device = advertisement_data[ble_address].device
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=False)

    pprint(await curtain_device.get_device_data())
    pprint(await curtain_device.get_basic_info())
    await curtain_device.set_position(100)


if __name__ == "__main__":
    asyncio.run(main())
```
