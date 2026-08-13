# M3 Developer Evidence Template

This directory is a template only. It records no test result and must not be
used as M3 acceptance evidence. Copy it to the delivery-specific evidence path
after the USER approves a candidate implementation commit.

## Required contents

- `environment/system.json`, `devices.txt`, and `packages.txt`
- `checksums/SHA256SUMS` for config, fixture, and native artifact identities
- one `cards/M3-<DOMAIN>-<NNN>.md` file for every RPI-NATIVE Test ID
- `logs/`, `results/`, and `media-metadata/` indexes with sanitized data only

Each card must state the Test ID, status, branch and full 40-character
implementation SHA, hardware and wiring, artifact identity, config and
fixture hashes, exact command, USER observations where required, timestamps,
exit code, and result artifact paths. Unrun cards remain `Pending` or
`Blocked`; they are never `Pass`.
