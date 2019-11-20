# pySwitchbot [![Build Status](https://travis-ci.org/Danielhiversen/pySwitchbot.svg?branch=master)](https://travis-ci.org/Danielhiversen/pySwitchbot)
Library to control Switchbot IoT devices https://www.switch-bot.com/bot

This project is an initial fork from https://github.com/Danielhiversen/pySwitchbot with some major improvements targeted:

- [x] Improved error handling and retry logic when trying to connect to switchbots
- [x] Correct [Bluepy](https://github.com/IanHarvey/bluepy) API usage
- [x] Add password support (must set a password first in the Switchbot iOS/Android app)
- [x] Get current battery percentage and firmware version
- [ ] Get and set long press time settings
- [ ] Allow setting the password in an API
- [ ] Manage timers etc
- [ ] Switch between press and switch modes

The goal is to make this component work with [HomeAssistant](https://www.home-assistant.io/integrations/switchbot/) to give more flexibility to users of Switchbots without needing a SwitchBot hub.

Hopefully this project will address some of the shortcomings in the official Switchbot [open API](https://github.com/OpenWonderLabs/python-host).

Please raise any feature requests as issues. 

[Buy me a coffee :)](https://paypal.me/nemccarthy)
