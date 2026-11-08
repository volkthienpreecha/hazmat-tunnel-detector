# Hazmat System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build both controller applications, offline dashboard, autonomous demo and simulator.
**Architecture:** Shared MicroPython-compatible control core; board-specific adapters; ESP32 gateway and CPython simulator expose the same HTTP API.
**Tech Stack:** Python stdlib, MicroPython, browser HTML/CSS/JavaScript.
**Spec:** docs/superpowers/specs/2026-11-08-hazmat-system-design.md

## Global Constraints
- 200 ms peer heartbeat, 1000 ms peer timeout, 500 ms manual motion lease.
- No hardware fallback to fake measurements; unset pins inhibit hardware startup.
- Offline assets only; commands never automatically resume after recovery.
- Autonomous retreat is 2 seconds after 5 seconds ventilation, opt-in clear path only.
- User authorizes implementation now, sequential commits, public repository and named collaborator invitations.

## Review Focus
- Oversized UART frames recover without renewing permission to move (Task 1).
- Heartbeats cannot extend a manual drive command (Task 1).
- Sensor and communication faults prohibit autonomous retreat (Task 1).
- Slow HTTP clients cannot block the control loop (Task 3).
- Pointer cancel, browser blur and stale state stop and disarm controls (Task 4).

### Task 1: Protocol and safety core
Files: firmware/shared/{protocol,control}.py, tests/test_core.py.
Interfaces: FrameParser.feed(bytes)->list[dict]; encode(dict)->bytes; Controller.update(now,inputs), command(now,action,payload); snapshot(now)->dict.
- [x] Write unittest cases for framing, replay, finite/type/range rejection, heartbeat/lease separation and autonomous transitions.
- [x] Run python3 -m unittest discover -s tests -v and observe missing-module failure.
- [x] Implement bounded framing and pure control core with injected monotonic time.
- [x] Run whole suite, require pass; commit.

### Task 2: Firmware and hardware configuration
Files: firmware/{motion,hazard}/main.py, firmware/shared/{hardware,runtime}.py, firmware/config.example.json, tools/package_firmware.py, docs/hardware.md.
Interfaces: Hardware.read()->dict; Hardware.apply(snapshot); UartPeer.poll(now), send(frame); shared core from Task 1.
- [x] Write fake-machine tests for unconfigured pins, safe outputs, ADC/I2C conversion and bounded UART pump.
- [x] Observe red, implement adapters/entrypoints and test again.
- [x] Document exact supported model assumptions, fan driver and power routing; commit after whole suite passes.

### Task 3: Gateway and simulator
Files: firmware/shared/http.py, firmware/hazard/gateway.py, simulator/server.py, tests/test_http.py.
Interfaces: GET /api/state; POST /api/command with token, action and payload; simulator-only POST /api/scenario.
- [x] Write API/parser tests for authentication, malformed bodies, bounds and simulator scenario control.
- [x] Observe red; implement bounded async server, AP startup and simulator loop sharing control logic.
- [x] Test faults, two-node exchange and slow requests, run whole suite; commit.

### Task 4: Dashboard
Files: dashboard/{index.html,style.css,app.js}, tests/browser.mjs, PRODUCT.md, DESIGN.md.
Interfaces: Task 3 API, hold-to-run renewal at 150 ms with no queued motion.
- [x] Write browser assertions for arming, manual drive/release, autonomy, stop and stale state before implementing.
- [x] Implement readable dark instrument layout with glass control layer and responsive fallback.
- [x] Run browser checks at desktop and mobile widths and inspect actual rendered output; commit.

### Task 5: Integration and handoff
Files: README.md, docs/{protocol,bench-test}.md, .github/workflows/test.yml, task ledger.
- [x] Fresh reviewer checks complete branch against spec, focusing on safety and runtime compatibility.
- [x] Add regression tests for material findings, repair, run suite/package/browser checks.
- [x] Record verification and hardware limits, commit; create public repo, push and invite resolved collaborators.
