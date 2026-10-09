# pySwitchbot [![codecov](https://codecov.io/gh/sblibs/pySwitchbot/graph/badge.svg?token=TI027U5ISQ)](https://codecov.io/gh/sblibs/pySwitchbot)

Library to control Switchbot IoT devices https://www.switch-bot.com/

## Setting up the environment

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## OAuth account access

pySwitchbot provides helpers for SwitchBot's authorization-code flow. The
calling application supplies a SwitchBot-issued client ID and its registered
redirect URI; neither value is tied to Home Assistant or embedded in the
library.

SwitchBot currently treats these integrations as public clients: the token
request does not use a client secret, and the authorization server does not
support PKCE. The caller must generate an unpredictable, single-use `state`,
store it for the duration of the flow, and reject callbacks whose state does
not match. State protects the callback from request forgery but does not
replace PKCE.

```python
import secrets

from switchbot import (
    build_oauth_authorize_url,
    exchange_oauth_code,
    fetch_cloud_devices_by_token,
)

state = secrets.token_urlsafe(32)
authorize_url = build_oauth_authorize_url(client_id, redirect_uri, state)

# Store state before sending the user to authorize_url. On callback:
if callback_state != state:
    raise ValueError("OAuth state mismatch")

token = await exchange_oauth_code(
    session,
    client_id,
    redirect_uri,
    authorization_code,
)
devices = await fetch_cloud_devices_by_token(session, token["access_token"])
```

The client ID and exact HTTPS redirect URI must be registered with SwitchBot;
arbitrary values and wildcard redirect URIs will not work. `exchange_oauth_code`
returns the provider's token mapping after validating the access token and
normalizing `expires_in` to an integer. The access token can then be passed to
`fetch_cloud_devices_by_token` or
`SwitchbotEncryptedDevice.async_retrieve_encryption_key_by_token`.

HTTP 401 and 403 responses from the SwitchBot account API raise
`SwitchbotAuthenticationError`. Other API failures raise `SwitchbotApiError`,
while transport and availability failures raise
`SwitchbotAccountConnectionError`.

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
- **`..., status code: 190`** (`SwitchbotApiError`) — authentication succeeded
  but the key could not be read. Usually the account is not the device
  **owner**: keys are only returned to the owning account, not to shared/family
  members. Retrieve the key from the owner account, or transfer ownership in
  the app.

The key only needs to be fetched once; store the `key_id` and encryption key
and reuse them — there is no need to call the script on every connection.

## Examples:

#### WoLock (Lock-Pro)

Unlock:

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock
from switchbot.const import SwitchbotModel

BLE_MAC = "XX:XX:XX:XX:XX:XX"  # The MAC of your lock
KEY_ID = "XX"  # The key-ID of your encryption-key for your lock
ENC_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # The encryption-key with key-ID "XX"
LOCK_MODEL = SwitchbotModel.LOCK_PRO  # Your lock model (here we use the Lock-Pro)


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

BLE_MAC = "XX:XX:XX:XX:XX:XX"  # The MAC of your lock
KEY_ID = "XX"  # The key-ID of your encryption-key for your lock
ENC_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # The encryption-key with key-ID "XX"
LOCK_MODEL = SwitchbotModel.LOCK_PRO  # Your lock model (here we use the Lock-Pro)


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(
        wolock[BLE_MAC].device, KEY_ID, ENC_KEY, model=LOCK_MODEL
    ).lock()


asyncio.run(main())
```

#### Subscribing to state changes

Every device exposes `subscribe(callback)`, which registers a zero-argument
callback and returns an unsubscribe function. The callback fires whenever the
device's parsed state changes — after an active `update()` poll, and, while a
connection is open, when the device pushes an unsolicited notification.

The callback takes no arguments: read the new state from the device's accessors
(e.g. `get_lock_status()`) when it fires.

Locks push real-time updates while connected. `lock()` / `unlock()` enable
notifications for the duration of the operation, so if the lock is operated
manually during that window the callback fires with the updated status:

```python
import asyncio
from switchbot.devices import lock
from switchbot.discovery import GetSwitchbotDevices
from switchbot.const import SwitchbotModel

BLE_MAC = "XX:XX:XX:XX:XX:XX"
KEY_ID = "XX"
ENC_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
LOCK_MODEL = SwitchbotModel.LOCK_PRO


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    device = lock.SwitchbotLock(
        wolock[BLE_MAC].device, KEY_ID, ENC_KEY, model=LOCK_MODEL
    )

    def on_change():
        print("lock status:", device.get_lock_status())

    unsubscribe = device.subscribe(on_change)

    await device.update()  # fires the callback with the current status
    await device.unlock()

    unsubscribe()


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
