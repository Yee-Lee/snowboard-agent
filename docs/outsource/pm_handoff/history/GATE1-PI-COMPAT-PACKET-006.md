# GATE1-PI-COMPAT-PACKET-006 — Product Pi Compatibility

- **Packet ID**: `G1-PI-COMPAT-006`
- **Revision**: `2026-08-23-r1`
- **Status**: `USER APPROVED / CORE PACKET ACK REQUEST / NO EXECUTION AUTHORIZATION`
- **Authority requested from**: Core Designer
- **Parent authority**: `ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001`
- **Execution owner**: LLM POC Test Controller
- **Reviewer**: POC Technical Lead / User, then Core Designer

## 1. Purpose and non-credit boundary

This packet performs the narrow physical-Pi eligibility filter required to close External Gate 1.
It runs only the two candidates frozen by Core and proves that the pinned aarch64 runtime/model pair
can be installed offline, loaded, driven through the product child protocol and cleaned up on the
target Pi. It does not execute or claim any M4B-P1–P12 result, performance threshold, resource gate,
thermal result, provisional finalist, final winner or product baseline.

No Gate 1 output may be copied, renamed, linked or ingested into Gate 2A evidence. Gate 2A uses
`G2A-PI-LLM-001`, a new run ID and `poc_llm/evidence/m4b/2a/`.

## 2. Frozen candidates and no-backfill rule

| Order | Candidate ID | Model artifact | SHA-256 | Size bytes |
| ---: | --- | --- | --- | ---: |
| 1 | `CAND-LRT-G4E2B-MOBILE-R1` | `gemma-4-E2B-it.litertlm` | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` | `2588147712` |
| 2 | `CAND-LRT-Q25-15B-Q8-R1` | `Qwen2.5-1.5B-Instruct_multi-prefill-seq_q8_ekv4096.litertlm` | `faa60663b333290c1496c499828b21d3e3254a788cacd8cce917ce0f761a2dc9` | `1597931520` |

Runtime is `litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl`, SHA-256
`5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00`, Apache-2.0. The
installed native library must hash to
`9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` and resolve every ELF
dependency.

`CAND-LRT-Q25-05B-Q8-R1` and all other candidates are ineligible. A `FAIL` or `INCONCLUSIVE` result
does not create a replacement slot. Ordering is retained from the accepted UTM engineering input;
this packet applies compatibility eligibility only and does not rerank candidates.

## 3. Exact target environment

The controller must fail before artifact installation unless every mandatory field is proven:

| Field | Required value |
| --- | --- |
| Hardware | Raspberry Pi 5, 4GB physical RAM |
| OS | Debian GNU/Linux 13 |
| Architecture | `aarch64` |
| Swap | `SwapTotal: 0 kB`; no zram/zswap swap device |
| Git | clean checkout at the packet's full 40-character execution SHA |
| Network during install/run | no IPv4 route and no non-loopback IPv6 route |
| Power/cooling | recorded supply/cooling identity; `vcgencmd get_throttled=0x0` before launch |
| Clock | UTC timestamps plus monotonic durations |
| Artifact root | `/tmp/llm-poc-g1-pi-006/artifacts` |
| Fresh install root | `/tmp/llm-poc-g1-pi-006/install` |
| Evidence root | `/tmp/llm-poc-g1-pi-006/evidence/<run-id>` |

The operator may stage authenticated artifacts before disabling the network. The runner may not
change swap, network configuration, boot configuration, clocks, governor, cooling, privileges or
system packages. Any required host change is a separate operator authorization.

## 4. Frozen protocol/config envelope

- Protocol: `snowboard.llm/1` plus explicit `PING`/`PONG` lifecycle frames locked by this revision.
- Driver: LiteRT-LM CPU, four threads, synchronous `conversation.send_message()`.
- One Engine remains resident for the compatibility lifecycle; each request creates a fresh
  conversation and closes it after the terminal frame.
- Input/output envelope: maximum 128 input tokens, maximum 16 output tokens, temperature `0.0`,
  top-p `1.0`.
- READY deadline: 10 seconds from child spawn.
- Generation deadline: 15 seconds.
- Cooperative cancel bound: 500 ms; TERM wait 2 seconds; KILL wait 1 second; rebuild is not part of
  Gate 1 compatibility.
- Runtime download, network fallback and fallback model are disabled.

The one compatibility generation uses the public deterministic input below. Model text is never
retained; the runner validates the normalized product result and stores only terminal type,
action-kind, schema disposition, timing and hashes.

```json
{
  "perceptions": [{"kind": "read", "status": "ok", "text": "Choose the rest action."}],
  "pending_message_count": 0,
  "capabilities": {"perceptions": ["read"], "actions": ["rest"], "tools": []}
}
```

## 5. Required executable flow

The final reviewed SHA must contain `run_gate1_pi_compat_v6.py`, the Pi config/candidate/acquisition
manifests, protocol/config/result schemas and an immutable checksum lock. The only scored command is:

```sh
python3 poc_llm/tools/run_gate1_pi_compat_v6.py \
  --packet-lock poc_llm/harness/gate1-pi-compat-lock-v6.json \
  --candidate-set poc_llm/fixtures/gate1/pi-compat-candidates-v6.json \
  --execution-sha <approved-full-sha> \
  --run-id <G1-PI-COMPAT-006-UTC-ID> \
  --evidence-root /tmp/llm-poc-g1-pi-006/evidence
```

The runner owns these steps and stops on the first prelaunch identity violation:

1. authenticate packet/source SHA, clean worktree, schemas, runner, adapter, manifests and every
   artifact checksum;
2. prove the exact target environment and fresh run/install/evidence paths;
3. install the dependency-free wheel offline without copying a workstation environment;
4. verify installed Python/native identity, ELF architecture, linkage and license record;
5. for each frozen candidate in order, start a new process group and require exact-identity READY;
6. send PING and require PONG; send the single compatibility GENERATE and require one schema-valid
   RESULT; send SHUTDOWN and require SHUTDOWN_ACK;
7. require leader exit `0`, waitpid completion, zero process-group members and zero run-owned file
   descriptor/thread residue; and
8. preserve raw controlled evidence outside Git and emit one sanitized per-candidate result plus an
   aggregate eligibility result.

## 6. Evidence and schema minimum

Each candidate result must include packet/run/source/candidate/config/runtime/model/runner/fixture
hashes; platform observations; READY/PONG/generation/SHUTDOWN timing; terminal and normalized schema
status; stderr byte count/hash; cleanup signals, exit/waitpid and orphan count; start/end UTC; raw
artifact relative paths/hashes; result; and violations.

Allowed result values are `PASS`, `FAIL` and `INCONCLUSIVE` only:

- `PASS`: every preflight, identity, offline install/import, READY/PONG, one deterministic
  generation, SHUTDOWN, exit and cleanup criterion succeeds.
- `FAIL`: a valid target run proves incompatibility or a mandatory lifecycle/cleanup criterion
  fails.
- `INCONCLUSIVE`: evidence or target validity is lost such that compatibility cannot be decided.

An aggregate proposed-finalist list contains only the original candidates with per-candidate
`PASS`, preserves their original order and cannot exceed two. No metric from this packet may be
labelled P1–P12.

## 7. Retry and abort rules

- Prelaunch identity/environment failure: no candidate launch; fix only through a new packet/SHA.
- Valid candidate `FAIL`: no retry in the same revision.
- Infrastructure/evidence interruption: at most one identical rerun in a fresh run ID after the
  Technical Lead records why the first result is `INCONCLUSIVE`.
- OOM, kernel fault, swap activity, unexpected network route, dirty path, checksum drift, protocol
  desynchronization or cleanup uncertainty: stop the entire packet and preserve the attempt.
- Never overwrite an attempt or alter fixtures/config/thresholds after observing a result.

## 8. Exit and next Core decision

After User/Technical Lead review, submit the immutable packet SHA and sanitized aggregate to Core.
Core must issue a written Gate 1 Finalist ACK naming zero, one or two eligible candidate IDs and the
reviewed evidence manifest SHA. Gate 2A remains blocked until that ACK exists, even if both
compatibility runs pass.
