# Software verification record

Date: 2026-11-08. Hardware was not connected.

- `python3 -m unittest discover -s tests -v`: 26 passing tests covering framing,
  replay/session recovery, manual leases, obstacle/tilt/power input validation,
  hazard filtering, fan response, autonomous retreat and peer failure,
  UART backpressure/stop priority, old HTTP command ordering, sensor conversions
  and slow HTTP client isolation.
- `node tests/browser.mjs`: Chromium acceptance covers autonomous start, gas
  hazard -> stop/fan, emergency-stop latch, reset/rearm, manual hold/release,
  desktop/mobile width, horizontal overflow and JavaScript errors. Screenshot
  artifacts are local/CI outputs, not committed generated source.
- `PYTHONPYCACHEPREFIX=/tmp/hazmat-pycache python3 -m compileall -q firmware simulator tools`
  and `node --check dashboard/app.js`: Python/JS syntax checks.
- Both board filesystem packages built with `tools/package_firmware.py`.
- Fresh whole-system code review found four actionable defects. Regressions
  reproduced them before fixes: lost stop under telemetry, stale buffered drive,
  one-shot hello/startup deadlock, and rearm reviving a previous drive. All have
  executable coverage in `tests/test_transport.py`; HTTP ordering is in
  `tests/test_http.py`. No performance or certified-safety claims follow.

CPython compilation is not MicroPython-on-board validation. GPIO allocation,
ADC voltage accuracy, physical UART timing, display geometry, actual AP firmware
API, motor/servo direction, electrical limits, RF behavior, calibrated thresholds
and safe rear clearance remain unchecked. Use `docs/bench-test.md`.

Bounded consolidation: the independent review and regressions support keeping
transport backpressure, boot ordering, and stale-command tests together in this
project. They do not support a cross-project policy change. No global skill or
permission changes were made.
