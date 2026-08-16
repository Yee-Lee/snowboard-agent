# DELIVERY-M3-HARDWARE-VALIDATION-001

Status: **Superseded evidence — exact-SHA retest required**

The 20 JSON files currently under `results/` were produced for implementation
SHA `bae36dcb2684a14a129be1e90f3533451d280820`. They do not validate the M3
candidate containing the CR_M3_I fixes and must not be cited as PASS.

The junior developer handoff is `docs/runbooks/m3_rpi_validation.md`. The
revised runner refuses a mismatched candidate SHA or dirty `src/`, `tests/`,
`pyproject.toml`, or `requirements/` tree. A valid rerun creates/updates:

- `manifest.json` for one candidate SHA;
- `environment/system.json`, `hardware.json`, `devices.txt`, and `packages.txt`;
- `checksums/SHA256SUMS`;
- 20 `cards/M3-*.md` and 20 schema-complete `results/M3-*.json` files;
- `logs/` and `media-metadata/index.json`.

Until all 20 cards have been regenerated and the independent Tester report is
committed, this delivery remains Pending and M3 is not Accepted or Closed.
