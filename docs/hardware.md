# Hardware build and wiring design

This is the assembly plan, not a record of an assembled or tested rover. Exact
board revisions, gas/temperature parts, motor specifications and driver are still
unconfirmed. `config.example.json` intentionally contains no guessed GPIOs.

## Mechanical arrangement

Use an RC chassis with two rear drive motors and a front steering servo/linkage.
Mount both Feather boards on insulated standoffs. Put the ultrasonic module at
the front with an unobstructed view. Mount the IMU rigidly, with +Z upward when
level. Keep gas and temperature sensors away from motor heat and fan exhaust.
Use a short sampling duct near the gas sensor if desired, but do not assume
that a ventilation fan can clear a tunnel or that intake flow moves the chassis.
Secure the battery and cables against wheel/linkage movement.

## Bill of materials and interfaces

| Part | Quantity | Firmware interface / requirement |
| --- | --- | --- |
| ESP32-S3 TFT Feather | 2 | Confirm exact regular/reverse TFT revision |
| RC chassis, rear motors, steering linkage | 1 | Two brushed DC motors and a servo |
| Dual H-bridge driver | 1 | Separate PWM, IN1, IN2 per motor; rated above measured motor stall current |
| RC steering servo | 1 | 50 Hz PWM; confirm pulse range mechanically |
| RCWL-1601 | 1 | Trigger/echo driver assumes HC-SR04-compatible pulse protocol; confirm module variant |
| LSM6DSO/LSM6DSOX breakout | 1 | I2C; WHO_AM_I 0x6c, configured ±2 g / ±250 dps |
| INA219 breakout | 1 | I2C; configure actual shunt resistance and load ratings |
| Gas sensor/module | 1 | Analog ADC module; model, heater supply, warmup and divider must be confirmed |
| TMP36 or course temperature sensor | 1 | Implemented analog conversion is TMP36 only; other models need their own driver |
| Fan and logic-level MOSFET driver | 1 | GPIO gate input, separate correctly rated load supply, external gate pulldown |
| Regulated actuator supply | 1 | Match servo and fan voltage/current; typically separate from logic regulator |
| Battery, fuse, main switch | 1 each | Chemistry/cell count and regulator matched to motors; current safety defaults assume 2S |
| Breadboard, headers, jumpers, terminals | As needed | Breadboard only for logic/sensor signals |

Choose actual power components from motor stall current, servo stall current,
fan inrush and sensor heater requirements. Do not buy from an unverified drawing.
No parts have been purchased or installed by this build.

## Power topology

```text
Battery + -> fuse -> physical master switch -> motor-driver VM -> rear motors
                                        +-> actuator regulator -> servo + fan
                                        +-> appropriate logic regulators -> Feathers
Battery - ------------------------------- shared ground -------------------

Feather #1 PWM/IN1/IN2 -> dual H bridge -> left / right rear motor
Feather #1 servo signal ----------------> steering servo
Feather #2 fan GPIO -> gate resistor -> MOSFET gate
Fan + -> actuator supply; Fan - -> MOSFET drain; MOSFET source -> ground
Gate -> external pulldown -> ground
Flyback protection across the fan/load as required by the actual fan driver
```

Do not feed a 2S LiPo directly into a Feather's single-cell battery socket.
Use USB for first logic tests. Verify the board's permitted USB/5V input and
power-sharing behavior before adding a regulator or powering from two sources.
Motor/fan currents must use rated wires/terminals, not breadboard power rails.
A physical motor-power stop switch is independent of the dashboard.
A watchdog reset cannot by itself establish electrical motor braking; driver
inputs/enable require appropriate external pull resistors so reset means off.

## Signal wiring and pin assignment worksheet

Solder headers if absent, then straddle the breadboard center channel or use two
breadboards if the Feather blocks the connection holes. Disconnect load power
while wiring. GPIO numbers are ESP32 GPIOs, not arbitrary breadboard positions.

| Board | config key | Connection |
| --- | --- | --- |
| #1 | uart_tx | #2 uart_rx |
| #1 | uart_rx | #2 uart_tx |
| Both | GND | Common signal ground |
| #1 | sda, scl | IMU + INA219 shared I2C; pullups to 3.3 V |
| #1 | i2c_power | Optional board regulator-enable GPIO; check exact Feather pinout |
| #1 | trig, echo | Ultrasonic trigger/echo; level-shift echo if above 3.3 V |
| #1 | motor_left/right_pwm, a, b | Driver PWM and direction inputs; configure driver enable separately |
| #1 | servo | Servo signal only; servo power uses load regulator |
| #2 | gas_adc | Gas analog output through verified divider/protection |
| #2 | temp_adc | Confirmed TMP36 output, within ADC input voltage limits |
| #2 | fan | MOSFET driver logic input, not motor current |
| #2 | display.* | Built-in ST7789 SPI, control and power pins for the exact board |

ESP32 inputs are not 5 V tolerant. Confirm the sensor output maximum at its
supply voltage before connection. MQ-type heaters may need a dedicated supply
and a long initial burn-in; 60 seconds is a software example, not a calibration
instruction. Raw ADC thresholds are demonstration values, not gas ppm.
`gas_adc_scale` records the chosen divider but does not calibrate the raw ADC
alarm thresholds. They must be re-established for that circuit.

INA219 load wiring is in series: supply + -> VIN+ -> shunt -> VIN- -> monitored
load +. Its I2C VCC/GND wiring is separate. Ensure monitored current never
exceeds the breakout/shunt ratings; select a different sensor for high stall
currents. Current firmware reports bus voltage at VIN- and shunt-derived current.

## Configuration and first power-on

1. Photograph part labels and read their datasheets. Resolve every null GPIO
   using the actual Feather pinout, reserving USB, onboard TFT and flash pins.
2. Copy `firmware/config.example.json` to an ignored `config.local.json` for each
   board. Set role, pins, actual shunt, temperature model and gas warmup.
3. For hazard board, set a unique AP password (12+ characters), a random operator
   token (24+ characters), and correct TFT pins/offsets. Enable display after a
   text-only test. Store secrets locally; never commit them.
4. Firmware currently validates missing/duplicate pins, but cannot infer which
   GPIOs are electrically usable on a particular board. Verify that manually.
5. Set `hardware_confirmed` only after the worksheet and power routing are
   checked. Keep `allow_clear_path_retreat` false for first tests.
6. Test with wheels lifted, current-limited supplies and motor power disconnected
   initially. Follow `bench-test.md` before putting it on the floor.

## Primary references

- [Adafruit ESP32-S3 TFT Feather](https://learn.adafruit.com/adafruit-esp32-s3-tft-feather?view=all)
- [Adafruit reverse TFT Feather pinouts](https://learn.adafruit.com/esp32-s3-reverse-tft-feather/pinouts)
- [ST LSM6DSOX datasheet](https://www.st.com/resource/en/datasheet/lsm6dsox.pdf)
- [TI INA219 datasheet](https://www.ti.com/lit/ds/symlink/ina219.pdf)

Driver register configurations follow these documents, but have not been
validated on a physical board. Ultrasonic pulse conversion, ADC behavior,
MicroPython AP keywords and TFT geometry must pass the bench checks.
