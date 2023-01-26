##### [🔙Back to Home](https://github.com/prithvi2k2/Alexa-VoiceUI-Controlled-Drone/#alexa-voiceui-controlled-drone)
---

This directory contains the __custom python ground control station(GCS) application which will be communicating between the Alexa skill and drone__

- Install all packages from `requirements.txt` in the local environment of GCS
- Python version 3.6 is recommended as it is tested on the same
- Run `main.py` with an optional connection string argument like `--connect /dev/ttyUSB0` for specifying the telemetry radio receiver's port connected to GCS
- If no connection string is provided, it will default to `dronekit-sitl` or another simulator setup
- Custom connection strings(for both real drone's telemetry receiver or alternate simulator) can be set as default in `droneActions.py` file

## Known issues

None