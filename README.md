# pySwitchbot [![Build Status](https://travis-ci.org/sblibs/pySwitchbot.svg?branch=master)](https://travis-ci.org/sblibs/pySwitchbot)

Library to control Switchbot IoT devices https://www.switch-bot.com/bot

## Obtaining locks encryption key

Using the script `scripts/get_encryption_key.py` you can manually obtain locks encryption key.

Usage:

```shell
$ python3 get_encryption_key.py MAC USERNAME
Key ID: XX
Encryption key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Where `MAC` is MAC address of the lock and `USERNAME` is your SwitchBot account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

Examples:

- Lock-Pro

Status:

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    print()
    print(wolock)


asyncio.run(main())
```

Unlock:

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock
from switchbot.const import SwitchbotModel

BLE_MAC="XX:XX:XX:XX:XX:XX" # The MAC of your lock
KEY_ID="XX" # The key-ID of your encryption-key for your lock
ENCRYPTION_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # The encryption-key with key-ID "XX"

async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(
        wolock[BLE_MAC].device, KEY_ID, ENCRYPTION_KEY, model=SwitchbotModel.LOCK_PRO
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
ENCRYPTION_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # The encryption-key with key-ID "XX"

async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(
        wolock[BLE_MAC].device, KEY_ID, ENCRYPTION_KEY, model=SwitchbotModel.LOCK_PRO
    ).lock()


asyncio.run(main())
```
