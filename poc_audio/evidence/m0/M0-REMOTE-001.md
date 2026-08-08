# M0-REMOTE-001 — Remote control and evidence-chain readiness

## Test packet

| Field | Value |
| --- | --- |
| Delivery requirement | Final checklist §§1, 2, 5, and 8; M0 exit gate |
| Purpose | Prove authenticated remote control, Pi/audio inventory, explicit cancellation, cleanup, and checksum-preserving evidence transfer. |
| Target | Operator-managed target host (Raspberry Pi 5 Model B Rev 1.1) |
| Preconditions | Pi powered and reachable; operator-managed key authentication; no audio workload running. |
| Command | `M0_SSH_CONFIG=/protected/path/config bash poc_audio/tools/m0_remote_readiness.sh <operator-alias> <evidence-directory>` |
| Pass gate | Correct Pi identity; remote nonzero exit code and remote timeout observed; isolated probe is absent after cancel; local/remote/round-trip SHA-256 values match; no named temporary files or audio device owners remain. |
| Cleanup | The runner sends `TERM` to its explicit probe PID and removes its named remote `/tmp` marker. A final read-only inspection checks the named process/file patterns and `/dev/snd/*` owners. |

## Results

| Run | Result | Evidence |
| --- | --- | --- |
| 2026-08-08 | `PASS` | Protected operator evidence bundle (not stored in Git); source SHA `5a3983c3af483c2c89742e9c30aa1978934b52ee` |

The passed run recorded remote exit code `37`, a remote timeout exit code `124`,
an explicit probe PID with
`cancel_cleanup=PASS`, and identical source/remote/round-trip SHA-256 values.
It also proves the named transfer file was removed and that no audio device had
an owner after the test. The environment inventory records a 4 GB Raspberry Pi
5 with the Google Voice HAT capture/playback device and `throttled=0x0`.

## Finding retained

An earlier ad-hoc test used a background child directly from an SSH shell. Its
stdout/stderr inherited the SSH channel, so local timeout did not provide a
reliable cancellation boundary and left a `sleep 120` child (PID 1247). It was
explicitly terminated and verified absent before the passed run. This is a
`FAIL` for that control method, not a failure of the Pi or SSH transport.

Rule for all later remote tests: do not use SSH disconnect/timeout as cleanup
proof for a remote child. Start a uniquely identified process with closed
standard streams, record its PID, explicitly cancel it, and verify absence.

## Remaining M0 work and risk

- The passed control path is ready for non-privileged remote commands and
  evidence transfer. The dedicated connection profile is operator-managed and
  deliberately excluded from this repository.
- Audio capture/playback lifecycle, I2S format verification, and all M3 HAL
  behaviour remain out of scope until M1/M3 respectively.
- One transient local-network name-resolution failure was observed and recovered
  on retry. Run the pre-test before each hardware session; escalate to a
  local-only stable mapping if it recurs.

## Runbook

For a fresh workstation, Pi checkout selection, pre-test, and Git/Pi sync, use
[`poc_audio/README.md`](../../README.md). This packet records only the M0 test
contract, result, retained finding, and M0-specific risk.
