# Protocol v1

UART: 115200 baud, 8N1, crossed TX/RX and common ground, 3.3 V logic. Each frame
is a UTF-8 JSON object ending in LF. Maximum encoded frame is 1024 bytes including
LF. Malformed/oversized frames discard through the next newline.

```json
{"v":1,"kind":"telemetry","session":"random-boot-id","seq":12,"data":{"hazard":"normal"}}
```

Kinds: hello, heartbeat, telemetry, arm, drive, inspect, stop, reset, ack.
Sequence is increasing per boot session, integer 0..2147483646. New sessions
require hello once a receiver has a session; periodically repeated hello allows
staggered startup. Session changes disarm the receiver. Retired sessions remain
rejected, with eight changes permitted per receiver boot to bound memory.
Restart after exhausting this limit. UART is not an authenticated physical bus.

Hazard-to-motion telemetry includes `hazard` (warming, normal, warning, danger,
fault). Motion-to-hazard includes distance_cm, tilt_deg, voltage, current_a,
acceleration_g, gyro_dps and motion state. Ack includes original frame seq,
accepted and motion state. Gateway displays board telemetry, not optimistic
command results. HTTP command response `queued` is not a board acknowledgment.

Telemetry is scheduled every 200 ms; a hello replaces one periodically.
Motion requires fresh hazard telemetry within 1000 ms. Only valid hazard telemetry
renews peer health; heartbeat alone never renews a drive lease. Manual commands
have a separate 500 ms lease. Pending actuator commands expire in the sender
within 200 ms. Stop preempts buffered telemetry/commands and resynchronizes any
partial frame before sending. Invalid frames never renew permissions.

Motion command data:
- drive: throttle -0.5..0.5, steering -1..1, finite numbers, no booleans.
- arm / inspect / stop / reset: empty object.
- stop latches; reset requires healthy normal inputs and leaves motion disarmed.
- inspect requires arming and enters bounded phase logic; it is autonomous and
  does not require manual command renewal. Peer loss still stops it.

## Same-origin HTTP API

GET `/api/state`: aggregated measurements, mode, age, controller state and event
history (40 entries). All data is on the local AP; no CORS or cloud dependency.

POST `/api/command`, JSON `{"action":"drive","payload":{"throttle":0.3,"steering":0}}`.
Headers: Content-Type application/json, X-Operator-Token, X-Operator-Session
(random tab ID), X-Command-Seq (strictly increasing per tab). Request ordering
rejects delayed older commands after release/stop. At most eight tab sessions per
gateway boot; restart if exhausted. One operator lease of 2000 ms arbitrates
clients. Stop is permitted to any authenticated operator regardless of lease.

POST `/api/scenario`, JSON `{"scenario":"gas"}`: simulator-only fault injection.
Other scenarios: normal, heat, obstacle, tilt, power, sensor_fault, peer_loss.
Use simulator token `demo-token`; hardware requires generated credentials.

HTTP: 4 concurrent clients, 4096-byte headers, 2048-byte bodies, 2 second total
request timeout. No chunked encoding. Static asset paths are allowlisted and
streamed in 1024-byte chunks. Cross-origin browser commands are rejected.
Local HTTP is unencrypted; use only on the isolated password-protected demo AP.
