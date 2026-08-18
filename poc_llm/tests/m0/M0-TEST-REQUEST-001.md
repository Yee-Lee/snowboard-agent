# M0-TEST-REQUEST-001 — Environment and Evidence-chain Readiness

- **Packet ID**: `M0-PACKET-001`
- **Status**: `DRAFT / NOT AUTHORIZED FOR PI EXECUTION`
- **Internal milestone**: M0
- **Delivery areas**: D1, D5, D8
- **Developer**: LLM POC Developer
- **Execution owner**: POC Test Controller
- **Evidence reviewer**: Technical Lead
- **Acceptance owner**: Internal Tester
- **Python**: 3.11+
- **Third-party dependencies**: none
- **Model/runtime download**: prohibited

This packet is executable from a clean checkout without a model download. Local execution only
validates the deterministic harness. It does not start M0 or produce Pi hardware acceptance.

## Entry Conditions for a Pi Run

1. External Gate 0 is recorded `COMPLETE`; milestone index explicitly sets M0 `IN_PROGRESS`.
2. User approves the exact SHA, operator-managed SSH target, temporary `/tmp` marker transfer,
   cleanup, and read-only inventory commands. Installation, reboot, privilege and network changes
   remain separately prohibited unless explicitly approved.
3. Workstation and Pi checkouts are clean and resolve to the same exact 40-character SHA.
4. `LLM_POC_SSH_TARGET` is provided by operator SSH configuration; endpoint, username, key path
   and host fingerprint are not written to repo or evidence.
5. Raw evidence destination is outside Git and has an operator-approved retention policy.

## Setup and Lock Verification

Allowed commands from `poc_llm/`:

```sh
python3 --version
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 2)'
python3 -m venv .venv
.venv/bin/python -c 'import sys; print(sys.version.split()[0])'
.venv/bin/python tools/run_m0_dummy_packet.py
```

Expected: version check exits `0`; no package installation or network access occurs; runner exits
`0` and returns JSON with overall `PASS`, three case results, terminate/kill exit codes and
`orphan_zero=true`.

## Deterministic Lifecycle Cases

| Case | Timeout | Expected result | Cleanup proof |
| --- | ---: | --- | --- |
| `M0-DUMMY-GRACEFUL` | READY 2s; exit 1s | ping + shutdown, exit `0` | process group absent |
| `M0-DUMMY-TERMINATE` | READY 2s; exit 1s | SIGTERM, exit `-15` | `Popen.wait()` and group absent |
| `M0-DUMMY-FORCE-KILL` | TERM grace 250ms; exit 1s | ignored TERM escalates to SIGKILL, exit `-9` | `Popen.wait()` and group absent |

Any missing frame, timeout, unexpected exit, remaining process group or incomplete output is
`FAIL` for a valid environment. Python/OS mismatch or corrupted/incomplete evidence is
`INCONCLUSIVE`.

## Allowed Read-only Pi Inventory

Run only after the entry approval. Capture command, UTC timestamp, exit code and sanitized output:

```sh
ssh "$LLM_POC_SSH_TARGET" 'uname -a'
ssh "$LLM_POC_SSH_TARGET" 'uname -m'
ssh "$LLM_POC_SSH_TARGET" 'getconf GNU_LIBC_VERSION'
ssh "$LLM_POC_SSH_TARGET" 'cat /proc/device-tree/model'
ssh "$LLM_POC_SSH_TARGET" 'cat /proc/meminfo'
ssh "$LLM_POC_SSH_TARGET" 'df -B1 /'
ssh "$LLM_POC_SSH_TARGET" 'cat /sys/class/thermal/thermal_zone0/temp'
ssh "$LLM_POC_SSH_TARGET" 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'
ssh "$LLM_POC_SSH_TARGET" 'vcgencmd get_throttled'
ssh "$LLM_POC_SSH_TARGET" 'git -C <approved-pi-checkout> rev-parse HEAD'
ssh "$LLM_POC_SSH_TARGET" 'git -C <approved-pi-checkout> status --porcelain'
```

`vcgencmd` or cpufreq absence is recorded as environment evidence and may make the relevant case
`INCONCLUSIVE`; it must not be hidden by retrying or installing tools during the packet.

## Transfer and Cleanup Case

The operator must replace `<approved-local-raw-dir>` and `<approved-pi-checkout>` before packet
freeze. The only permitted Pi write is a uniquely named marker below `/tmp`; cleanup targets that
exact file, never a directory or wildcard. Commands must be copied into the frozen request with a
literal validated marker name before execution.

Required observations: workstation SHA-256, uploaded Pi SHA-256, downloaded SHA-256 are identical;
the exact Pi marker and local returned marker are absent after cleanup. Failure to prove absence is
`FAIL`; missing transfer evidence is `INCONCLUSIVE`.

## Evidence

- Schema: `poc_llm/evidence/m0/m0-evidence.schema.json`.
- Raw stdout/stderr and remote inventory remain outside Git; record their SHA-256 and controlled
  location in the reviewed sanitized index.
- Never capture endpoint, username, key path, host fingerprint, secret, private prompt/model data.
- Required fields include exact SHA, packet/schema version, commands, UTC timestamps, exit codes,
  environment, raw artifact checksum, result, cleanup and reviewer/acceptance decision.

## Resource Schedule and Retry

- Developer local validation: 0.5 working day; Pi execution: 0.5 day after availability; evidence
  review and Internal Tester confirmation: 0.5 day.
- Pi 5 4GB/8GB availability: `Blocked — pending operator confirmation`.
- Storage budget: <50 MiB; model/artifact download: 0.
- Each case permits at most one controlled rerun after an identified environment correction. Keep
  the original result and reason. Further reruns require a change request and new packet version.
