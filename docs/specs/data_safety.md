# AR1 Data-Safety Specification

Status: `AUTHORITATIVE / FROZEN AT AR1M0`

Git contains only source, schemas, sanitized manifests, documentation, and
reviewed sanitized evidence. Models, binaries, wheels, raw or private audio,
sensitive transcripts, credentials, private keys, operator endpoints,
operator configuration, and unsanitized raw results stay outside the worktree.

The default local gate is:

```text
python3 -m asr_r1.tools.check_data_safety
```

It scans visible tracked and untracked worktree files, excludes Git internals
and disposable build/cache directories, rejects controlled/raw directory
locations, rejects known model/binary/audio suffixes, and detects a bounded set
of high-confidence secret signatures. Passing the scan does not declassify a
file: human review remains required before sanitized evidence is committed.
