# DELIVERY-M3-HARDWARE-VALIDATION-001

Status: **Accepted for M3 at implementation SHA `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`**

The authoritative M3 closeout evidence is indexed at
`designer-review-5c9e5aa-20260817/README.md`.  Under the USER-approved transition
direct-review disposition, Designer reconciled 20 unique target Test IDs across two
preserved debug runs: all results are `Pass` with exit code 0, all identify the fixed
SHA and config checksum, and all three manual checklists passed.  `CR_M3_I` records
the final acceptance decision.  No second freeze was required.

## Superseded legacy bundle

The 20 JSON files currently under `results/` were successfully regenerated for
implementation SHA `cab627705c341d0058e0c395e96d0be10c4c4239`. They pass the
automated hardware gate and are ready for the independent Tester report.

The junior developer handoff is `docs/runbooks/m3_rpi_validation.md`. The
revised runner refuses a mismatched candidate SHA or dirty `src/`, `tests/`,
`pyproject.toml`, or `requirements/` tree. A valid rerun creates/updates:

- `manifest.json` for one candidate SHA;
- `environment/system.json`, `hardware.json`, `devices.txt`, and `packages.txt`;
- `checksums/SHA256SUMS`;
- 20 `cards/M3-*.md` and 20 schema-complete `results/M3-*.json` files;
- `logs/` and `media-metadata/index.json`.

This legacy `cab627...` bundle remains superseded and is not the basis of M3
acceptance.  It is retained only for audit history.
