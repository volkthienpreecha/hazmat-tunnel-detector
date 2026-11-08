# Hardware acceptance checklist

Nothing here has been checked on physical hardware yet. Record board firmware
version, part numbers, pinout, measured voltages, timestamps and pass/fail results.

- [ ] Inspect common ground, polarity, fuses, regulator ratings and driver pulldowns.
- [ ] Verify logic inputs remain within 3.3 V limits, including ultrasonic echo and gas output.
- [ ] Power each Feather from USB alone and confirm safe motor outputs at boot/reset.
- [ ] Confirm I2C IDs, axes and IMU mounting, actual shunt resistance, zero/current reading against a meter.
- [ ] Validate ADC voltage against a meter, TMP36 temperature against a reference, gas warmup/calibration per sensor datasheet.
- [ ] Read raw sensors without motors; disconnect each sensor and document whether that hardware can detect the fault.
- [ ] Check fan driver, supply and flyback protection, then confirm warming/fault/danger fan behavior.
- [ ] Verify ST7789 pins, offset, orientation and text. Confirm display writes never starve the safety loop.
- [ ] Boot boards in both orders; confirm UART recovers, reports freshness, and remains disarmed.
- [ ] Wheels lifted: test one motor at a time, directions, PWM limits, steering endpoints without binding.
- [ ] Confirm voltage/current/tilt/obstacle stop thresholds for the actual chassis and battery. Defaults assume a 2S classroom demo.
- [ ] Hold manual forward, release, cancel touch, blur browser and disconnect Wi-Fi. Measure actual stop latency; require command output to stop within 500 ms of the last valid command plus one control-loop cycle.
- [ ] Disconnect UART while driving; require stop at 1000 ms peer timeout plus one loop cycle. Heartbeats alone must not keep manual driving alive.
- [ ] Emergency stop during every autonomous phase and under browser polling/UART traffic. It must latch, reset must not move, reconnect must not move.
- [ ] Trigger a hazard using a safe sensor test/simulation method, never intentionally create a toxic or flammable atmosphere. Verify immediate stop before filtered clearing.
- [ ] In a short clear mock tunnel, test Inspect -> Ventilate -> Finished with retreat disabled.
- [ ] Only after confirming clear rear path, enable retreat and verify 5 s ventilation -> 2 s reverse -> stopped. This is timed motion, not accurate return-to-origin.
- [ ] Inject tilt, low voltage, sensor fault and peer loss during ventilation/retreat; confirm no reverse movement on fault.
- [ ] Check watchdog reset and physical motor-power switch independently of software.
- [ ] Run all tests again after changing configuration or drivers.

No real hazardous environment deployment is authorized or validated by these
checks. Neither the classroom gas sensor nor the fan establishes clearance.
