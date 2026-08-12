# Display POC hardware verification

The display hardware workflow follows the proven Audio POC pattern:

1. Keep SSH endpoint/account/key configuration outside Git.
2. Test only an exact, clean full-SHA checkout on both workstation and Pi.
3. Run a read-only remote pre-test before touching the display.
4. Run the capability packet locally on the Pi; do not treat SSH timeout or disconnect as cleanup proof.
5. Record explicit `PASS`, `FAIL`, or `INCONCLUSIVE`, then verify SPI/GPIO owners are absent.
6. Keep raw evidence ignored; publish only a reviewed, sanitized summary packet.

## Fixture preparation

Copy `poc_display/config/ssd1351_pi5.example.json` to an operator-managed run config. Fill in:

- the physical Waveshare module revision;
- the resolved integer `gpio.chip` visible on this Pi;
- any fixture-specific value that differs from the example.

Do not edit source defaults or pass deployment pins through environment variables. The operator confirms the module/revision and wiring as `PASS`; photos are not required.

## Workstation/Pi pre-test

Create an operator-managed SSH config and select the exact Pi worktree and config:

```sh
M3_SSH_CONFIG=/protected/path/ssh-config \
PI_POC_REPO=/protected/path/to/pi-worktree \
PI_DISPLAY_CONFIG=/protected/path/to/config.actual.json \
bash poc_display/tools/environment_pre_test.sh <operator-alias>
```

The pre-test is read-only. It gates Pi 5/aarch64 identity, exact clean SHA, required tools, config hash, SPI/gpiochip device presence, boot SPI configuration, temperature/throttling inventory, and absence of current SPI/GPIO owners.

## Pi-local M3 capability packet

After the pre-test passes, run from the clean Pi checkout. Operator visual fields are explicit evidence, not assumptions:

```sh
M3_PANEL_REVISION='<revision printed on the module>' \
M3_FIXTURE_RESULT=PASS \
M3_COLOR_RESULT=PASS \
M3_ORIENTATION_RESULT=PASS \
M3_FLICKER_RESULT=PASS \
bash poc_display/tools/m3_ssd1351_capability.sh \
  /protected/path/to/config.actual.json
```

The packet performs:

- clean native build and checksum/custody only for artifacts not included in the Git submission unit;
- ABI/config validation;
- black, white, red, green, blue and gradient frames;
- wrong-length and missing-SPI-device rejection;
- idempotent stop and three reopen cycles;
- 10 warm-ups plus at least 100 full-frame latency samples;
- post-run SPI/gpiochip owner cleanup;
- operator-attested fixture/wiring, revision, color order, orientation and flicker gates; photos are not required.

Missing tools/hardware/operator evidence produce `INCONCLUSIVE` (exit 2). A failed asserted behaviour produces `FAIL` (exit 1). Only all gates passing produces `PASS` (exit 0).

## Evidence handling

Raw directories under `poc_display/evidence/m3/<timestamp>-*/` are Git-ignored. Review them locally, redact private paths or environment details, and publish a sanitized Markdown summary directly under `poc_display/evidence/m3/`. A summary must cite the full source SHA, config and artifact checksums, environment, automated results, operator visual observations, known limits, and raw evidence custody location without exposing SSH details.

Do not run the remote-control probe or unrelated workloads during latency measurement. If a remote command ever starts a child process, record its PID, close its standard streams, cancel it explicitly, and verify absence—the Audio POC showed that disconnecting SSH is not cleanup proof.
