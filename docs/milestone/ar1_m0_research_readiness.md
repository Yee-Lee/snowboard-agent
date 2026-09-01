# AR1M0: Contract Intake and Research Readiness

Status: `COMPLETE`

Create a clean, governed starting point without executing a real model.

## Exit gate

- Contract and receipt indexed.
- Branch, control SHA, milestone, tag, privacy, and evidence rules fixed.
- Legacy tree isolated and recoverable from `audio_m4`.
- Candidate tracker and Whisper/Silero control provenance created.
- Fixture reuse audit and milestone collection plan created without collecting
  audio or prematurely assigning holdout.
- Minimal streaming result/lifecycle schemas and fake/unit tests pass.
- Data-safety and default test-discovery checks pass.

Only then may `asr_r1_m0` be created and AR1M1 begin.

## Exit evidence

| Gate | Evidence | State |
| --- | --- | --- |
| Contract and receipt | Inbound contract, outbound ACK, verified SHA-256 | `PASS` |
| Governance identities | `asr_r1`, immutable `audio_m4` SHA, tag/privacy/evidence rules | `PASS` |
| Legacy isolation | `AR1M0-LEGACY-CLEANUP-001`; predecessor recoverable at `audio_m4` | `PASS` |
| Candidate tracking | `asr_r1/manifests/candidate_tracker.json`; unresolved identities fail open into AR1M1 | `PASS` |
| Control provenance | `AR1M0-CONTROL-PROVENANCE-001` and machine-readable Whisper/Silero record | `PASS` |
| Fixture planning | Frozen M0–M3 collection gates and reuse-audit plan; no audio collected and no role assigned | `PASS` |
| Protocol scaffolding | Lifecycle, PCM, and result schemas plus dependency-free fake runtime | `PASS` |
| Unit/discovery gate | Default unittest discovery finds and passes all AR1M0 tests | `PASS` |
| Data safety | Visible-worktree scan finds no prohibited content | `PASS` |

Verification commands:

```text
python3 -m unittest discover -v
python3 -m asr_r1.tools.check_data_safety
python3 -m asr_r1.tools.check_m0_readiness
git diff --check
```

User reviewed the exit evidence and explicitly approved the qualification
commit, annotated tag, and push on 2026-09-01. All listed gates pass. No real
model was acquired, built, imported, loaded, or executed. The completion commit
is identified by immutable annotated tag `asr_r1_m0`; AR1M1 remains
`NOT_STARTED` until a separate entry update records its authorization and
preconditions.
