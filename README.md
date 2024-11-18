# pySwitchbot [![Build Status](https://travis-ci.org/sblibs/pySwitchbot.svg?branch=master)](https://travis-ci.org/sblibs/pySwitchbot)

Library to control Switchbot IoT devices https://www.switch-bot.com/bot

## Obtaining locks encryption key

Using the script `scripts/get_encryption_key.py` you can manually obtain locks encryption key.

Usage:

```shell
$ python3 get_encryption_key.py MAC USERNAME
Key ID: xx
Encryption key: xxxxxxxxxxxxxxxx
```

Where `MAC` is MAC address of the lock and `USERNAME` is your SwitchBot account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

Examples:

- WoLock

```python
import asyncio
from switchbot.discovery import GetSwitchbotDevices
from switchbot.devices import lock


async def main():
    wolock = await GetSwitchbotDevices().get_locks()
    await lock.SwitchbotLock(wolock['32C0F607-18B8-xxxx-xxxx-xxxxxxxxxx'].device, "key-id", "encryption-key").get_lock_status()


asyncio.run(main())

```
