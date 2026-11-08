# Hazmat Tunnel Detector: proposed software design

Status: approved by user on 2026-11-08, including autonomous demo amendment below.

## Intent and scope

Build the software for a two-ESP32 classroom inspection rover: controller
firmware, local communication, browser dashboard, and a hardware-free simulator.
The operator should see measurement freshness and hazards, drive the rover,
stop it, and observe automatic ventilation. Deliver in sequential local commits.
Hardware assembly and hardware validation follow later.

Interpretation of the request: include both controller applications and the
communication/dashboard workstream, but no hardware assembly. Real sensor
drivers require confirmed sensor models; do not silently substitute demo data.
This is an educational prototype, not evidence that a tunnel is safe to enter.

## Approaches

1. Recommended: one repository, MicroPython controllers, dependency-light static
   dashboard served by ESP32 #2, same-origin HTTP API, CPython simulator.
   Works without internet and shares protocol and logic tests across targets.
2. Separate dashboard and firmware repositories: independent releases, but
   unnecessary protocol/version coordination for this three-person project.
3. Hosted React dashboard plus gateway: richer framework tooling, but adds
   deployment and connectivity dependencies. No need for them for this scope.

Recommendation is a builder proposal, not an already-approved user decision.

## Repository layout

- `firmware/shared/`: bounded framing, validation, protocol and control logic.
- `firmware/motion/`: ESP32 #1 entrypoint, motion safety and hardware adapters.
- `firmware/hazard/`: ESP32 #2 entrypoint, sensing, ventilation, TFT, AP and API.
- `dashboard/`: offline static HTML, CSS, JavaScript, no CDN assets.
- `simulator/`: laptop server and simulated board/sensor scenarios.
- `tests/`: protocol, safety, API and browser interaction checks.
- `tools/`: package/copy firmware and dashboard onto the board filesystem.
- `docs/`: protocol, configuration, deployment and bench acceptance procedures.

## Controller ownership

The proposal duplicates actuator ownership and the earlier split assigns IMU
and power differently. Resolve this with one owner per physical actuator:

| Controller | Inputs | Outputs and responsibilities |
| --- | --- | --- |
| #1 Motion | RCWL-1601 distance, LSM6DSO IMU, INA219 power, UART | Both rear motors, steering servo, local obstacle/tilt/power stop, command timeout |
| #2 Hazard/gateway | Gas, temperature, UART | Fan, TFT, hazard processing, local Wi-Fi AP, dashboard/API |

UART connects the controllers. Controller #2 aggregates telemetry and forwards
operator intent; #1 decides whether motion is permitted. A hazard stop must
override operator motion. The fan cannot be disabled by the operator during an
active hazard. Fan operation is mitigation in the demo, never proof of clearance.

## Protocol and safety contract

- Versioned newline-delimited JSON with a strict maximum frame length, bounded
  receive buffers and a parser that recovers after malformed/oversized frames.
- Validate types, ranges, finite numbers, message kind, protocol version,
  sender session identity and increasing sequence number before acting.
- Heartbeat interval: proposed 200 ms. Peer timeout: 1000 ms. Motion command
  lease: 500 ms, refreshed while the operator holds a driving control.
  Use wrap-safe monotonic timing on the boards.
- Heartbeats never refresh motion leases. Stale, replayed or malformed commands
  never renew permission to move. Reboot or reconnect disarms the system.
- Startup, expired command, missing peer, invalid safety sensor, obstacle,
  excessive tilt, configured power fault or hazard must stop drive outputs.
- Explicit arming after healthy fresh telemetry is required. Emergency stop
  latches; reset requires stopped controls and cleared faults, and never resumes
  motion automatically. Do not queue drive commands during reconnect.
- Record command acknowledgments and rejection reasons. The UI distinguishes
  requested state from board-reported state.
- Hazard states include warming-up, normal, warning, danger and sensor fault.
  Use configurable hysteresis and clearing dwell; an immediate high-reading
  path must bypass averaging. Unknown/invalid hazard readings inhibit motion.
- Gas is raw ADC/relative measurement until model-specific calibration exists.
  Temperature units require an explicitly selected sensor model. Battery
  voltage is displayed; percentage requires a configured battery model.

Exact schema, timing constants and state transitions will be locked in the
first implementation commit and covered by deterministic fake-clock tests.

## Gateway and browser behavior

ESP32 #2 hosts a password-protected AP and static dashboard using MicroPython
network and asynchronous socket APIs. AP range remains a physical limitation.
Avoid external fonts, map tiles, cloud services and internet-dependent assets.
The gateway uses bounded requests, timeouts and concurrent handling so slow
browser clients cannot block safety updates. Set a conservative client limit.

Proposed API: GET state and events; POST arm, drive, stop and reset. Use an
explicit operator session/token, same-origin checks and JSON request bodies.
One controller lease permits driving; other clients can observe. Generated
credentials live in ignored local configuration. No production secrets in Git.

Poll telemetry at approximately 4 Hz. Drive controls are hold-to-run, refreshing
the command lease while held. Release, pointer cancel, focus loss, hidden page,
disconnect or stale telemetry cancels driving and attempts a stop; local lease
expiry remains the reliable stop path. No automatic retries of motion commands.
Always-visible stop and keyboard-accessible controls, with clear focus states.

## Dashboard design brief

Product register: operational tool for a student operator monitoring a rover
on a laptop or phone. User references: Palantir-style information density,
the supplied Worldview image, Apple glass controls, and Unslop craft guidance.

Scene proposal: an operator at a dim tunnel entrance, focused on driving and
hazard changes. Use dark graphite surfaces, legible light type, cyan selection,
and amber/red exclusively for warning/fault meaning. No invented camera feed,
GPS position, geospatial map or reconstructed tunnel from nonexistent sensors.

Unslop direction:
- Product: remote rover control and environmental telemetry.
- Character: precise, restrained, watchful.
- World: field instruments at a tunnel entrance.
- Moments: the main measurement trend and the functional driving control layer.
- Signature: a measurement-age readout attached to each telemetry source.

Desktop sketch:

```text
Hazmat / Rover 01       Simulation or hardware     Link age       Stop
---------------------------------------------------------------------
Sensor readings        Gas / temperature history       Drive + arm
with units and age     with real sample timestamps     and interlocks
---------------------------------------------------------------------
Controller health      Hazard and fan state            Event history
```

Phone: stop and connection status first, hazards and current readings next,
then thumb-sized drive controls, followed by history and diagnostics. Avoid
horizontal overflow. Keep numeric trends on solid surfaces. Glass is limited
to the navigation/control layer, with opaque and reduced-transparency fallbacks.
Use system sans-serif and tabular mono numbers, a 4 px spacing grid, semantic
HTML and text labels in addition to color. Respect reduced motion and keyboard
navigation. Prefer readable contrast over matching decorative screenshot effects.

States: boot/warm-up, simulation, unconfigured hardware, connecting, live,
warning, danger, latched stop, stale telemetry, disconnected, malformed response,
sensor fault and recovery. Never label missing data normal or safe.

## Simulator and hardware boundary

Run a local server that serves the exact dashboard and API shape, executes
shared protocol/control logic, and provides deterministic fault injection:
gas/temperature spikes, obstacles, sensor faults, peer loss, command expiry,
reboots and malformed messages. Clearly label simulation throughout the UI.

Hardware mode must never fall back to fake readings. Unknown pins remain unset;
startup validation rejects missing/conflicting assignments. Provide documented
adapter interfaces and a board configuration template. Complete model-specific
drivers only for confirmed components, marking remaining adapters unimplemented.
Do not claim firmware is flash-and-drive ready until actual board, sensor,
display, motor-driver and pin configurations are confirmed and bench-tested.

## Sequential implementation commits

0. Design, protocol decisions and task ledger.
1. Shared message protocol, fake clock and safety state machines with tests.
2. Motion firmware and explicit hardware/configuration boundaries.
3. Hazard firmware, ventilation logic, gateway AP and HTTP API.
4. Simulator and fault-injection integration tests.
5. Dashboard, responsive styles and control interactions.
6. Integration repairs, browser evidence, deployment tools and bench checklist.

Use local commits; pushing/public repository creation remains dependent on
working GitHub access. Never publish attachments or local credentials.

## Acceptance and limits

Verify framing recovery, invalid types/ranges, sequence/session replay, bounded
memory, tick rollover, startup inhibit, immediate hazard response, hysteresis,
fan override protection, obstacle stop, lease expiry despite valid heartbeat,
disconnect, rearm and reset behavior. Exercise HTTP limits and slow requests.

Exercise desktop and phone dashboard views, keyboard and pointer driving,
release/cancel/blur stop, stale telemetry, reconnect without movement, event
history, unit labels and simulation labeling. Record commands and results in
the task ledger. Review integrated code and repair material findings.

Hardware-dependent timing, electrical behavior, sensor calibration, TFT driver
compatibility and real RF loss tests remain a separate bench acceptance step.
No claims of certified safety, accurate gas ppm, autonomous mapping, or reliable
underground radio coverage. Autonomous avoidance can be supplied as a bounded
demo state machine but stays disabled pending chassis/steering validation.

## References and tooling preparation

- Apple Materials: https://developer.apple.com/design/human-interface-guidelines/materials
- MicroPython WLAN: https://docs.micropython.org/en/latest/library/network.WLAN.html
- Unslop by Damir Sokolovsky, CC BY 4.0:
  https://github.com/heydamir/unslop/tree/a6f121eee5f29c2f74976b75456feae8b66afb3a

Unslop installed and matching reviewed source; official Apple page downloaded
to `/tmp/hazmat-apple-materials.html`. Local project memory search returned no
matching lessons. No application implementation or tests have run yet.

## Approved autonomous demo amendment

User approved Inspect -> Hazard stop -> Ventilate -> timed Retreat -> Finished.
Start is explicit; inspection drives slowly with live sensing. Hazard stops
immediately and runs the fan. After 5 seconds ventilating, a 2 second reverse
retreat is allowed only if a clear straight retreat path has been explicitly
configured and peer/safety telemetry remains fresh. Otherwise remain stopped.
No rear sensor is present; timed reversing cannot establish arrival at the start.
Communication loss, invalid sensor, tilt, power fault and emergency stop prohibit
retreat. An obstacle stops inspection without commanding an unvalidated turn.
No automatic reset or resume; fan remains on while the hazard persists.
Hardware deliverables are software adapters, wiring/power design, BOM and bench
procedures; physical assembly is not possible from this software environment.
