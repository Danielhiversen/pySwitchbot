#!/usr/bin/env python3
import getpass
import sys

from switchbot import SwitchbotLock


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <device_mac> <username> [<password>]")
        exit(1)

    if len(sys.argv) == 3:
        password = getpass.getpass()
    else:
        password = sys.argv[3]

    try:
        result = SwitchbotLock.retrieve_encryption_key(sys.argv[1], sys.argv[2], password)
    except RuntimeError as e:
        print(e)
        exit(1)

    print("Key ID: " + result["key_id"])
    print("Encryption key: " + result["encryption_key"])


if __name__ == "__main__":
    main()
