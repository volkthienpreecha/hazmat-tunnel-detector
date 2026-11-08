# Hazmat Tunnel Detector

MECH100 dual-ESP32 inspection rover with an offline field dashboard, MicroPython
controller applications and a two-node UART simulator.

## Try it without hardware

Requires Python 3.9+; the simulator has no Python package dependencies.

```sh
python3 -m simulator.server
```

Open [the local dashboard](http://127.0.0.1:8080). Enter operator token
`demo-token`, click **Connect controls**, then **Arm rover**. Hold the directional
buttons or use arrow/WASD keys to drive. Release to stop. **Emergency stop** or
Escape latches a stop; **Reset stop**, then rearm, to continue.

For an autonomous demo, arm and choose **Start inspection**. Change the simulation
scenario to Gas hazard: the rover stops and the fan runs. Default behavior stays
stopped. To demonstrate the full timed retreat sequence, start the simulator with:

```sh
python3 -m simulator.server --allow-retreat
```

Then hazard response is 5 seconds ventilating followed by 2 seconds reversing.
This is not mapping or guaranteed return to the starting point. Real retreat
requires an explicitly confirmed clear rear path; there is no rear range sensor.

## Architecture

| ESP32 #1 | ESP32 #2 |
| --- | --- |
| Rear motors and steering servo | Gas + temperature |
| Ultrasonic, LSM6DSO, INA219 | Fan + TFT |
| Local motion safety + autonomous phases | Wi-Fi AP + dashboard/API |

Versioned UART connects the boards. Manual drive leases expire after 500 ms;
peer timeout is 1000 ms. Hazard and sensor faults inhibit motion. The dashboard
shows board-reported state and measurement age. Automatic inspection continues
without a held manual command, but still stops on peer/sensor faults.

## Hardware and firmware

Start with [hardware design and wiring](docs/hardware.md), then the
[bench checklist](docs/bench-test.md). GPIOs are intentionally unset until actual
components and board pinouts are confirmed. Only the TMP36 analog temperature
conversion is implemented; gas thresholds are raw ADC demo values.

1. Install an appropriate official MicroPython ESP32-S3 image for the exact board.
2. Create ignored per-board `config.local.json` files from
   `firmware/config.example.json`; configure parts, pins, credentials and role.
3. Package each board filesystem:

```sh
python3 tools/package_firmware.py motion /tmp/hazmat-motion
python3 tools/package_firmware.py hazard /tmp/hazmat-hazard
```

4. Add that board's `config.local.json` to its package, then upload the **contents**
   to its MicroPython filesystem using your course-approved tool (Thonny or mpremote).
   `main.py`, `shared/` and, for the hazard board, `gateway.py` and `dashboard/`
   must be at the filesystem root. Reboot with motor power disconnected first.
5. Connect to the configured Hazmat-Rover AP, open the address printed on serial,
   and enter the configured operator token. No internet is needed.

Hardware support includes explicit PWM motor/servo/fan adapters, analog gas and
TMP36, LSM6DSO-family registers, INA219 shunt/bus measurement and minimal ST7789
text output. These have **not been exercised on physical boards**. Exact GPIO,
ADC voltage accuracy, ultrasonic protocol, display offsets, RF range, watchdog
and MicroPython API compatibility require bench verification. Do not connect
motors or a fan to ESP32 GPIO power or breadboard current paths.

## Tests

```sh
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
# Run the simulator in another terminal first:
npm run test:browser
```

The browser dependency is only for development checks; dashboard runtime needs
no Node, build step, CDN, account or cloud service. Browser test screenshots are
written to `output/playwright/` (ignored).

See [protocol](docs/protocol.md), [design](DESIGN.md) and
[implementation plan](docs/superpowers/plans/2026-11-08-hazmat-system.md).

## Project status

Software is a classroom prototype. It is not a certified gas detector or a safe
entry determination system. A local access point removes internet dependence;
it does not overcome underground radio attenuation. Assembly, electrical checks,
sensor calibration and chassis tests remain hardware work.

Design craft informed by [Unslop](https://github.com/heydamir/unslop) by Damir
Sokolovsky (CC BY 4.0), and [Apple Materials guidance](https://developer.apple.com/design/human-interface-guidelines/materials).
