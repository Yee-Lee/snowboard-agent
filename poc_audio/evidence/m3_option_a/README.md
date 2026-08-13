# M3 Option A validation evidence

This directory holds tracked, reviewed evidence for
`DELIVERY-AUDIO-POC-M3-VALIDATION-001`. Generate a local packet with:

```sh
bash poc_audio/tools/run_option_a_validation.sh prepare
```

Timestamped packet directories and their `raw/` contents are Git-ignored. They
may contain target-specific paths, environment details, and raw measurements.
Review and sanitize a completed packet before promoting its manifest, results,
or environment summary into this directory.

The `prepare` command does not exercise audio hardware. Every P4-A01 through
P4-A10 entry starts as `Pending`; only reviewed evidence may change a status to
`PASS`, `FAIL`, `INCONCLUSIVE`, or `Blocked`.
