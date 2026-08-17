# M3 candidate `5c9e5aa` — Designer direct-review evidence

## Scope and disposition request

This attachment is the complete Raspberry Pi 5 debug evidence collected for
candidate `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`.  The USER requested a
transition direct review: Designer may accept or reject this candidate from the
evidence without a separate Designer/Tester SHA-freeze gate.

This is not represented as a legacy single-run acceptance bundle.  It predates
the proposed interactive-runner workflow and consists of two preserved debug
runs.  The next comparable candidate should start with one complete interactive
run; incremental debug is then used only after that run fails.

## Included source runs

| Imported directory | Cards | Result |
| --- | ---: | --- |
| `run-audio-20260817/` | M3-AUDI-001, M3-AUDI-002, M3-AUDI-004 | 3 passed |
| `run-operator-20260817/` | M3-AUDI-003, M3-BTN-001~005, M3-CAMI-001~003, M3-DSPI-001~006, M3-GPIOI-001~002 | 17 passed after GPIOI-001 rerun |

Each imported run contains its raw pytest logs, result JSON, test cards,
manual observations, candidate manifest, config/artifact checksums, and
environment metadata.  Both runs identify the same full candidate SHA and the
same sanitized Pi-local config checksum:

```text
4d16d1a37007fcf29daebaf2d39c6ce427597bede0ccb0c2c0a396e582b0c7f7
```

## Transparency note

The first `M3-GPIOI-001` attempt in `run-operator-20260817/remaining-auto.log`
failed before hardware interaction because the invocation omitted
`SBD_M3_GPIO_OUTPUT_PIN` and `SBD_M3_GPIO_INPUT_PIN`.  It was rerun with the
required BCM17-to-BCM27 loopback variables; the successful raw log is
`gpioi-001-rerun.log`, and its result/card are included.  No evidence has been
deleted or replaced.

## Repository sanitization

Before repository intake, the local OS account was replaced with the pseudonymous
operator ID `operator-1`.  Absolute Core workspace and external Display artifact
paths were replaced with `<repo-root>` and `<external-display-artifact>` placeholders.
No result, status, timestamp, implementation/config/artifact/fixture checksum,
hardware identity, command arguments, manual observation, or failure log content was
removed.  The local config itself and all audio/photo/video media remain outside Git;
this bundle contains only the sanitized config path and its SHA-256 identity.

## Designer review checklist

1. Confirm every M3 target Test ID has one final `Pass` result for this SHA.
2. Review manual observations for AUDI-003, DSPI-002, and DSPI-005.
3. Confirm hardware/config/artifact identity is suitable for the intended
   release decision.
4. Record Accepted or Rejected, including any required follow-up.

## Designer disposition — 2026-08-17

**Accepted.** Designer reconciled exactly 20 unique target Test IDs.  Every final
result is `Pass` with exit code 0 and identifies implementation
`5c9e5aac47e7f4f0dd168d8c75541438ee74f858` plus config checksum
`4d16d1a37007fcf29daebaf2d39c6ce427597bede0ccb0c2c0a396e582b0c7f7`.
AUDI-003, DSPI-002, and DSPI-005 manual checklists contain only successful required
observations.  The first GPIOI-001 invocation failure and its successful corrected
rerun are both preserved, so the final result is auditable rather than overwritten.

Portable regression on the same implementation tree completed with `240 passed, 21
deselected`; selected tests contain no Fail, Blocked, Skip, or XFail.  The two-run
transition limitation is accepted only for this fixed M3 SHA under the USER's direct
review instruction.  Future candidates follow the current single-run workflow.
