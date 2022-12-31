# pySwitchbot [![Build Status](https://travis-ci.org/Danielhiversen/pySwitchbot.svg?branch=master)](https://travis-ci.org/Danielhiversen/pySwitchbot)
Library to control Switchbot IoT devices https://www.switch-bot.com/bot

## Obtaining locks encryption key
Using the script `scripts/get_encryption_key.py` you can manually obtain locks encryption key.

Usage:
```shell
python3 get_encryption_key.py MAC USERNAME
```
Where `MAC` is MAC address of the lock and `USERNAME` is your SwitchBot account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

[Buy me a coffee :)](http://paypal.me/dahoiv)
