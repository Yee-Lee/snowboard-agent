# GATE2A-PI-PACKET-001 — LLM-only Pi Validation

- **Packet ID**: `G2A-PI-LLM-001`
- **Revision**: `2026-08-23-r1`
- **Status**: `USER APPROVED / CORE PACKET ACK REQUEST / EXECUTION CONDITIONALLY BLOCKED`
- **Entry authority required**: Core Gate 1 Finalist ACK naming the candidate/evidence SHA
- **Execution owner**: LLM POC Test Controller
- **Reviewers**: POC Technical Lead / User, Internal Tester, Core Designer
- **Outcome ceiling**: provisional finalist recommendation; never final winner

## 1. Entry and independence

This packet executes M4B-P1–P8, P10A, P11 and P12 from zero on a physical Raspberry Pi 5. It may be
frozen and reviewed together with `G1-PI-COMPAT-006`, but no command may start until Core issues the
Gate 1 Finalist ACK. Only candidates named by that ACK run. No Gate 1 or workstation result supplies
a sample, repetition, PASS, threshold disposition or evidence file to this packet.

Each candidate uses a new `G2A-PI-LLM-001-<UTC>-<candidate>` run ID and
`poc_llm/evidence/m4b/2a/<run-id>/`. A candidate/config/fixture/schema/runner checksum change
invalidates every affected work package and requires a new packet revision before rerun.

## 2. Target and immutable identities

Target requirements are Raspberry Pi 5 4GB, Debian GNU/Linux 13 aarch64, `swap=0`, offline
execution, clean source checkout at the approved full SHA, authenticated LiteRT-LM 0.16.0 aarch64
wheel/native library and one of the Gate 1 ACK candidate identities. The 8GB Pi, if later requested,
uses the identical packet only for informational sanity and cannot repair a 4GB failure.

The runtime/model SHA-256 values, acquisition rules, four-thread CPU backend and no-download/no-
fallback rules are identical to `G1-PI-COMPAT-006`. Gate 2A uses independent Pi config files,
runner lock and evidence paths. Standard inference is fixed at maximum 128 input tokens, maximum 16
output tokens, temperature `0.0`, top-p `1.0`; only the separately locked P5 extreme profile changes
the output ceiling as described in §5.

## 3. Work-package order and stop conditions

| Order | Work package | Cases | Continue rule |
| ---: | --- | --- | --- |
| 1 | `G2A-WP01-PROVENANCE` | P11 | P11 `PASS` |
| 2 | `G2A-WP02-LIFECYCLE` | P1, P5, P6, P7 | P1/P5/P7 `PASS`; P6 `PASS` or valid conditional escalation backed by P7 |
| 3 | `G2A-WP03-OUTPUT` | P2, P3, P8 | P2/P3/P8 all `PASS` |
| 4 | `G2A-WP04-PERF-SOAK-OFFLINE` | P4, P10A, P12 | P10A/P12 `PASS`; P4 fully measured |
| 5 | `G2A-WP05-AGGREGATE` | decision table | all mandatory results reviewed |

Any mandatory `FAIL`, target/evidence invalidity, OOM, kernel fault, unexpected swap/network state,
checksum drift or uncertain cleanup stops later work packages for that candidate. Preserve all
completed and failed attempts without relabelling.

## 4. Common lifecycle and evidence rules

- READY must arrive within 10 seconds and contain exact candidate/runtime/model/config identity.
- stdin/stdout is schema-validated JSONL. PING/PONG, GENERATE, CANCEL, terminal frames and SHUTDOWN
  are correlated and reject extra/unknown fields.
- Every generation has exactly one terminal frame; duplicate/stale terminal frames fail.
- Each single-turn request creates and closes a fresh conversation; the Engine process is reused
  only where the case requires it.
- Candidate process groups are runner-owned. Cleanup is `SIGTERM -> 2 s wait -> SIGKILL if needed
  -> 1 s wait -> waitpid -> process-group/orphan/FD/thread check`.
- Raw prompt/model output/payload/credential/hidden context stays outside Git. Sanitized evidence
  stores fixed fixture IDs, terminal/action disposition, metrics and content hashes only.
- Primary capacity observation is `MemTotal - MemAvailable`; process-tree PSS/RSS, CPU, threads,
  temperature and throttling are diagnostics. `sum(RSS)` is never a capacity result.
- Each raw/sanitized item includes UTC and monotonic timestamps, source/lock/config/fixture/runner
  hashes, reproduction command, exit code, cleanup and raw relative path/hash.

## 5. Frozen case definitions

### P1 — persistent child lifecycle (`Mandatory`)

Perform three complete cold launch cycles. Each requires READY <=10 seconds, PING/PONG, one
standard deterministic generation, SHUTDOWN_ACK, exit `0`, waitpid and zero residue. Then keep one
child resident for ten PING/PONG exchanges and three sequential standard generations before clean
shutdown. Any framing, correlation, identity, deadline or cleanup failure is `FAIL`.

### P2/P3 — product output, fallback and log hygiene (`Mandatory`)

Use the precommitted 20-case public catalog, exactly three repetitions per case. Cases 001–010 run
model-backed valid speak/tool/rest/capability requests and must normalize to the exact product
schema with allowed action/tool/perception values. Cases 011–020 inject the frozen empty, invalid
JSON, unknown action/tool, empty speak, missing payload, illegal perception, refusal, extra-key and
leak-marker outputs directly at the reference normalizer boundary; every one must produce the
contract fallback without raising.

Normal cases require 100% schema validity across all repetitions. Failure cases require 100%
fallback validity. The scanner rejects prompt text, raw output, action payload, credentials, API
tokens/endpoints, hidden context and fixture leak markers in runner-owned stdout/stderr/logs. One
bad repetition is `FAIL`; no averaging is allowed.

### P4 — Pi performance (`Negotiable performance`)

Cold method: three independent clean child launches; record the first standard generation after
READY from each, then fully shut down. Hot method: one new persistent child, three discarded warmup
generations, then twenty recorded generations. Preserve raw wall time, TTFT, init time, prefill and
decode token counts/rates, process/system resource samples, P50/P95 and cleanup.

Starting targets are hot TTFT P95 <=2.5 seconds and hot decode throughput P50 >=4.0 tokens/second.
Meeting both may be reported `PASS`; missing either is `Core threshold decision required`, never an
automatic candidate `FAIL`. Missing raw samples or incomplete method is `INCONCLUSIVE`/`FAIL` based
on evidence validity and blocks provisional selection until resolved.

### P5 — physical-Pi 15-second timeout (`Mandatory`)

P5 is first executed against the model on the physical Pi; no workstation model result is required
or accepted. The locked P5 effective config differs from the standard config only as follows:

```json
{"test_profile":"p5-extreme-512","max_output_tokens":512,"generate_timeout_ms":15000}
```

The public extreme input is a 128-token-bounded `read` perception requesting a zh-TW `speak`
response of at least 300 Chinese characters, with only `speak` and `listen` capabilities and no
tools. It is `poc_llm/fixtures/gate2/p5-extreme-generation-001.json`, SHA-256
`01b3524db0ed51ec110ec207ba1795ed8c4fffc1ef56bcafb87e8f6fc974ef7a`, and is bound by the final
fixture lock before Core ACK.

`PASS` requires an `ERROR` terminal correlated to the request with code `TIMEOUT` and state `READY`,
emitted no earlier than 15.000 seconds and no later than 17.000 seconds. The generation worker must
be stopped; the same child must answer PING/PONG and shut down cleanly. The runner must then launch
the unchanged standard 16-token config, require READY, complete one standard probe, shut down,
waitpid and prove both process groups absent. If the model validly completes the extreme request
before 15 seconds, the predeclared case is `INCONCLUSIVE`, not `FAIL` or `PASS`, and Gate 2A cannot
close without a new Core-approved disposition. A hang, wrong terminal, late timeout, failed
recovery/rebuild or residue is `FAIL`. There is no adaptive second fixture after seeing the result.

### P6 — cooperative cancel (`Conditional escalation`)

Start the same frozen extreme generation and send correlated CANCEL after the first generation-
active observation. `PASS` requires CANCELLED <=500 ms, short-term resources released and READY
restored. Unsupported/native timeout is `Conditional escalation` only if all P7 Level 2, rebuild
and cleanup criteria pass. Late/uncorrelated results, false READY or leaked operation state fail.

### P7 — Level 2 force abort and Level 3 fatal outcome (`Mandatory`)

Start extreme generation, withhold cooperative success, then invoke one controller `force_abort()`:
SIGTERM, bounded wait, SIGKILL only if needed, waitpid and process-group absence. Recreate the
runtime manager/child from the unchanged lock, require READY <=10 seconds, execute one standard
probe, cleanly shut down and prove zero residue.

Separately inject a controller-owned rebuild-barrier failure without changing or corrupting model
artifacts. The harness must map failed force-abort/outer completion/rebuild to the documented fatal
outcome `exit 4`; it must not claim a systemd restart or call SIGTERM/SIGKILL Level 3. Real Level 2
and rebuild plus deterministic fatal mapping are both required.

### P8 — history isolation (`Mandatory`)

In one persistent child, execute five fixed single-turn requests containing unique public nonces and
traps referring to prior turns. Each request must create a fresh conversation. Store only response
hashes and scanner outcomes. No response may reproduce a prior nonce/trap, KV/context token count
must return to the frozen single-turn envelope, and final cleanup must pass.

### P10A — 20-session LLM-only soak (`Mandatory`)

Run the 20 fixed catalog inputs once each as independent single-turn sessions through one persistent
Engine, with a five-second interval after each terminal. For every session record terminal/schema
status, latency, process-tree PSS/RSS, `MemTotal`, `MemAvailable`, CPU, threads, temperature,
throttling and owner counts. Require 20/20 completion, history isolation, temperature <80°C,
`get_throttled=0x0`, no crash/OOM and final zero residue.

The memory-slope rule is frozen before results: compute ordinary least-squares slopes over sessions
6–20 for process-tree PSS and `MemTotal - MemAvailable`; each must be <=4.0 MiB/session. The median
of sessions 16–20 must also be no more than 64 MiB above the median of sessions 1–5 for both series.
All 20 samples are retained; no outlier removal is allowed. Exceeding either bound is `FAIL`;
missing/invalid samples are `INCONCLUSIVE` and block P10A closure.

### P11 — clean build and provenance (`Mandatory`)

From clean exact SHA and empty Pi install/run paths, verify OS/kernel/Python/hardware, source/config/
runner/schema/fixture checksums, runtime/model origin and license, offline wheel installation,
installed native library hash/ELF/linkage and reproduction commands. Any unknown source, checksum,
license, dependency or clean-build step is `FAIL`; missing controlled artifact is `Blocked` before
execution.

### P12 — offline inference (`Mandatory`)

Before model launch prove every non-loopback interface is link-down (including Wi-Fi and Ethernet),
there is no default or non-loopback route, DNS/proxy/API-token environment is absent and `swap=0`.
Repeat the same proof after the complete scored inference workload, and preserve the sanitized
interface/route/environment snapshots plus log scans. Any external connection,
credential/API endpoint transmission or incomplete network evidence is `FAIL`; no network may be
enabled between work packages in the scored run.

## 6. Exact command and required implementation bundle

The final reviewed SHA must contain one fail-closed controller, schemas, public fixture payloads,
candidate configs and a checksum lock. The only scored command is:

```sh
python3 poc_llm/tools/run_gate2a_pi.py \
  --packet-lock poc_llm/harness/gate2a-pi-lock-v1.json \
  --finalist-receipt <core-gate1-finalist-receipt-json> \
  --execution-sha <approved-full-sha> \
  --candidate-id <ack-named-candidate> \
  --run-id <G2A-PI-LLM-001-UTC-ID> \
  --evidence-root /tmp/llm-poc-g2a-001/evidence
```

The controller must reject Gate 1 packet IDs, run IDs, result paths and namespaces. It must reject
an ACK that does not name the candidate and Gate 1 evidence manifest SHA. Case subsets are not
scored execution; the official command always runs the ordered complete matrix.

## 7. Result schema and aggregate decision

Every P item has status `PASS`, `FAIL`, `INCONCLUSIVE`, `Blocked` or
`Core threshold decision required`, plus criteria, observations, raw paths/hashes and violations.
The candidate aggregate is eligible for a provisional-finalist recommendation only when:

- P1/P2/P3/P5/P7/P8/P10A/P11/P12 are all `PASS`;
- P6 is `PASS` or documented `Conditional escalation` with P7 fully `PASS`; and
- P4 has the complete method and either `PASS` or a resolved written Core threshold decision.

At most one candidate may be recommended after reviewing the complete frozen candidate set. The
User must approve any benchmark publication or candidate proposal before transmission. Core's Gate
2A response may name a provisional finalist only; Gate 2B remains blocked on a Core-recorded
Accepted Audio final handoff and real P9/P10B combined evidence.

## 8. Retry, review and cleanup

One identical rerun is allowed only for an evidence/infrastructure `INCONCLUSIVE`, after preserving
the first run and recording reviewer approval. A valid mandatory failure is not retuned or rerun in
this revision. Candidate/config/fixture/threshold/runner changes require a new revision and rerun of
all affected packages.

Before submission, the Technical Lead and Internal Tester verify exact SHA, target validity, raw
completeness, schema validation, calculations, log hygiene and zero residue. Benchmark numbers and
the provisional candidate proposal remain private until User approval.
