# AR1 Implementation Root

This directory contains AR1 source, tests, schemas, manifests, tools,
deliveries, and sanitized evidence. AR1M0 provides a dependency-free protocol
and fake runtime only; it has not acquired models or created real adapters.
Legacy code remains available at immutable tag `audio_m4` and must not be
imported directly.

Default local verification is:

```text
python3 -m unittest discover -v
python3 -m asr_r1.tools.check_data_safety
python3 -m asr_r1.tools.check_m0_readiness
```

The readiness command expects the milestone documents to record formal M0
completion. Until User approves that qualification commit, it deliberately
reports those final status rows as open.
