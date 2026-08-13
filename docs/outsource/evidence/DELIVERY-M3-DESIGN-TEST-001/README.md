# DELIVERY-M3-DESIGN-TEST-001 Evidence Index

- **Scope**: design / test-spec only
- **Implementation SHA**: `N/A - design/test-spec only`
- **Current hardware status**: `Pending`
- **Acceptance claim**: none

## Prepared evidence

| Evidence | Status | Location |
| :--- | :--- | :--- |
| Designer coverage review | Ready | `docs/reviews/history/TR_spec_M3_I.md` |
| Test platform / evidence contract | Ready | `docs/test_spec.md` §2 |
| M3 test cards / commands | Ready | `docs/test_spec/test_spec_M3.md` §3–§4 |
| Automated product implementation logs | Pending | Added after Developer exact-SHA delivery |
| Raspberry Pi cards | Pending | One card per `RPI-NATIVE` Test ID |
| OLED / speaker manual checklist | Pending | Added during target-device acceptance |

## RPI card rule

Each future card must include the hardware / wiring, full 40-character implementation SHA, artifact path + SHA-256, ABI, license / notice, sanitized config path + SHA-256, fixture SHA, exact command, operation steps, expected / actual result, timestamps and repository-relative artifact paths required by `EV-RPI` / `EV-MANUAL`.

POC evidence is design input only and must not be copied here as Core implementation acceptance. A card that has not been run stays `Pending`; missing target hardware is `Blocked`, never Pass.
