# M4A Tester re-verification evidence — candidate ed1b2cf

## Identity and verdict

| Field | Value |
| :--- | :--- |
| Candidate SHA | `ed1b2cf57581d48966a7dd6535c024ea51922b28` |
| Authoritative portable run | `m4a-ed1b2cf-20260828-p02` |
| Verdict | **Fail** |
| Target acceptance | Not started; portable entry gate failed |

The detached candidate checkout was clean for all protected paths. Raw logs remain
Git-external under `<tester-run-root>/m4a-tester-evidence-ed1b2cf-20260828-p02/`.

## Portable results

| Python | Result | Counts |
| :--- | :--- | :--- |
| CPython 3.11.16 | **Fail** | 166 passed, 1 failed, 0 skipped/xfailed |
| CPython 3.12.3 | Pass | 167 passed, 0 failed/skipped/xfailed |
| CPython 3.13.15 | Pass | 167 passed, 0 failed/skipped/xfailed |

The failing node was
`test_m4a_ipc_001_actual_asr_process_handles_coalesced_and_fragmented_input[False]`.
It completed the coalesced protocol path through nonempty result and
`SHUTDOWN_ACK`, then timed out in `Process.wait()` on Python 3.11. The unchanged
node failed again on the third independent repetition. A probe recorded
`returncode=0` and an absent `/proc/<pid>` at wait cancellation, proving the
child was already reaped while the asyncio transport waiter remained pending.

An initial `p01` attempt is retained separately and is not a candidate result:
the host's ROS Python 3.12 path caused Python 3.11 pytest plugin autoload to fail
before collection and before JUnit creation. `p02` removed the foreign
`PYTHONPATH` and disabled third-party plugin autoload.

## Directly affected and adjacent regression

- `tests/test_candidate_gate.py`: 14 passed.
- Full primary-version `not rpi`: 451 passed, 28 deselected.
- Tester-only proposed bounded-returncode patch: failing node 20/20 passed on
  CPython 3.11; four affected files 66 passed; full M4A manifest 167 passed.
- A proposed pre-ACK executor join still failed on repetition 2.
- A proposed bounded `communicate()` oracle still failed on repetition 9.
- Diagnostic patches were applied only to disposable Git-external worktrees and
  are not part of the candidate or formal evidence.

## Clean Pi baseline

The Tester rebooted the Pi before target work. Post-boot identity was aarch64,
CPython 3.13.5, boot ID `85777d3e-7dda-4ff5-8190-cc03901959f6`. There were zero
M4A processes, ALSA holders and ASR/TTS temp entries. No target preflight,
product run or acceptance was started because the portable matrix failed, so
no Pi result or card is claimed.

## Handoff

See `docs/reviews/TR_dev_M4_I.md` for the exact tested correction and bounded
minimum re-verification. Candidate `ed1b2cf57581d48966a7dd6535c024ea51922b28`
must remain immutable; the correction requires a new append-only candidate SHA.
