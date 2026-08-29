# ASSESSMENT — M3 Qwen Gate 2A Preflight Observation 001

- Date: 2026-08-29
- Run ID: `G2A-PI-QWEN-002`
- Execution source: `38002205f3769dd7d82ec45eb4b2030ec13990d1`
- Result: `INCONCLUSIVE / ENVIRONMENT PREFLIGHT / ZERO MODEL ACCESS`
- Gate credit: none

## Observation

The runner authenticated the Gate 1 entry and Gate 2A lock, allocated the new boot identity and then
failed the offline environment preflight before creating its evidence directory. P2, P3, P4, P5 and
P8 remained `Blocked`; runtime installation, receipt verification, model access and child launch did
not begin. The printed sanitized result is retained in the controller session. No candidate behavior
was observed and the run cannot affect candidate disposition.

## Cause and correction

`unshare --net` correctly removed routes, but the inherited host sysfs mount still exposed
`wlan0=up`; `offline_environment()` therefore rejected the otherwise isolated namespace. A no-model
probe proved that adding a private mount namespace and mounting read-only sysfs inside it exposes only
the namespace-local loopback interface while preserving zero routes, swap zero, `throttled=0x0`, the
clean exact SHA and the Pi's host Wi-Fi connection.

The replacement packet freezes that private-sysfs launch. The runner now allocates its controlled
evidence directory before isolation/environment preflight so any later early failure is saved as a
sanitized `INCONCLUSIVE` record. The retry requires a new boot ID, run ID and evidence root.
