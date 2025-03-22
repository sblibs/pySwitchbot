# pySwitchbot [![Build Status](https://travis-ci.org/sblibs/pySwitchbot.svg?branch=master)](https://travis-ci.org/sblibs/pySwitchbot)

Library to control Switchbot IoT devices https://www.switch-bot.com/bot

## Obtaining encryption key for Switchbot Locks

Using the script `scripts/get_encryption_key.py` you can manually obtain locks encryption key.

Usage:

```shell
$ python3 get_encryption_key.py MAC USERNAME
Key ID: xx
Encryption key: xxxxxxxxxxxxxxxx
```

Where `MAC` is MAC address of the lock and `USERNAME` is your SwitchBot account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

## Examples:

#### WoLock

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(wolock['32C0F607-18B8-xxxx-xxxx-xxxxxxxxxx'].device, "key-id", "encryption-key").get_lock_status()


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
        print() # print newline so that devices' data is separated visually

    # get the BLE device (via its address) and construct a curtain device
    ble_device = advertisement_data["9915077C-C6FD-5FF6-27D3-45087898790B"].device
    curtain_device = curtain.SwitchbotCurtain(ble_device, reverse_mode=False)

    pprint(await curtain_device.get_device_data())
    pprint(await curtain_device.get_basic_info())

    await curtain_device.set_position(100)


if __name__ == "__main__":
    asyncio.run(main())
```
