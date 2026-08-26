# GATE1-PI-COMPAT-PACKET-007 — Cumulative Stability and Core Integration Gate

- **Packet ID**: `G1-PI-COMPAT-007`
- **Revision**: `2026-08-26-r3`
- **Status**: `REVIEW FINDINGS REVISED / RE-REVIEW REQUIRED / EXECUTION NOT AUTHORIZED`
- **Replaces**: `G1-PI-COMPAT-006` for future Gate 1 execution
- **Formal credit requested**: M4B-P1, P6, P7, P10A, P11, P12
- **Execution owner**: LLM POC Test Controller

## 1. Cumulative boundary

P1～P12 are completed once across Gate 1 and Gate 2. This packet produces physical-Pi evidence for
P1, P6, P7, P10A, P11 and P12 while screening the two frozen candidates. Gate 2A does not repeat an
accepted item when its execution-surface, runtime/model/config/protocol/fixture, Pi and evidence-
manifest identities remain unchanged; it runs P2, P3, P4, P5 and P8. Gate 2B runs P9 and P10B plus
only change-affected regression. No result from `006`, UTM or workstation supplies P credit. P5
remains Pi-only.

The User requires reviewer approval of this design before execution. After reviewer approval, the
User may authorize execution while Core reviews the cumulative boundary. Results remain
`CORE ACCEPTANCE PENDING` and cannot close a gate until the Core ACK arrives.

## 2. Frozen candidates

| Order | Candidate | Model SHA-256 | Size bytes |
| ---: | --- | --- | ---: |
| 1 | `CAND-LRT-G4E2B-MOBILE-R1` | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` | `2588147712` |
| 2 | `CAND-LRT-Q25-15B-Q8-R1` | `faa60663b333290c1496c499828b21d3e3254a788cacd8cce917ce0f761a2dc9` | `1597931520` |

Runtime is LiteRT-LM v0.16.0 aarch64 wheel SHA-256
`5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00`; installed native-library
SHA-256 is `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4`.
Candidate order is fixed; no third candidate, fallback model, download or network fallback is allowed.

## 3. Target and authentication

Execution requires Raspberry Pi 5 4GB, Debian 13 aarch64, a clean full source SHA, `swap=0`, all
non-loopback interfaces/routes offline and `throttled=0x0` before and after the scored workload.

The v2 installer is the sole wheel-content authenticator. Each model must be an absolute regular
file with no write bits and is streamed through SHA-256 once before child launch, with a 120-second
deadline. The runner writes a strict receipt containing the digest and stable filesystem identity.
Every child authenticates the small receipt, config, protocol, prompt, response and receipt schemas,
then compares model metadata; no child rereads the full model. The final check compares metadata to
the receipt instead of rehashing the model.

The runner also records `execution_sha` for chronological provenance and
`execution_surface_sha256 = SHA256(gate1-pi-compat-lock-v7.json)` for carry-forward. Later evidence
or documentation commits may make the Gate 1 commit an ancestor rather than the current `HEAD`;
that alone is not source drift. Any changed artifact named by the lock changes the execution-surface
digest and invalidates only the P items influenced by that artifact.

## 4. Formal work packages

### G1-WP01 — P11 provenance and clean deployment

Authenticate clean source, lock, candidates, config, schemas, runner, fixture, runtime/model origin
and licenses. Install the wheel once offline into an empty path. Verify installed native SHA, ELF64
AArch64 and resolved linkage. Unknown identity/license, a dirty path or install failure is P11
`FAIL`; invalid environment/evidence before launch is `INCONCLUSIVE`.

### G1-WP02 — P1 normal lifecycle plus P10A stability

Launch one standard child. Exact-identity READY must arrive within 10 seconds after the one-pass
model authentication. Require PING/PONG and twenty fixed catalog inputs as sequential fresh single-
turn conversations in one persistent Engine. Each request must produce exactly one schema-valid
`RESULT` within 15 seconds. After every terminal, wait five seconds and record PSS/RSS, `MemTotal`,
`MemAvailable`, CPU, threads, temperature and throttling. Require SHUTDOWN_ACK, exit `0`, waitpid and
process-group absence.

P1 is `PASS` only when READY/framing/generation/shutdown/cleanup pass. P10A requires 20/20 sessions,
no crash/OOM, temperature below 80°C, `throttled=0x0`, and the frozen session 6–20 rules: PSS and
system-used OLS slopes each <=4.0 MiB/session; medians of sessions 16–20 are no more than 64 MiB
above sessions 1–5. No sample is dropped.

### G1-WP03 — P6 cancel and P7 force-abort/rebuild

Launch a fresh child, send the fixed public abort fixture, observe a generation-thread transition,
then issue correlated CANCEL. `CANCELLED` within 500 ms is P6 `PASS`; unsupported or completed-before-
cancel is `Conditional escalation`, eligible only if P7 passes. If neither an active generation nor
a terminal frame can be observed, the candidate evidence is `INCONCLUSIVE`, not `FAIL`.

Execute one Level 2 path on an active/pending generation: TERM, 2-second wait, KILL only if needed,
1-second wait, waitpid and process-group absence. Rebuild from the unchanged receipt, require READY/
PONG, complete one recovery generation, clean shutdown and orphan zero. Separately require the
deterministic controller fatal-outcome exit `4`; do not claim a product/systemd restart.

### G1-WP04 — P12 and cumulative receipt

P12 is `PASS` only when the same offline run has completed the P1 normal inference lifecycle and
the pre/post target observations both prove zero swap, no routes, all non-loopback interfaces down
and no sensitive environment names. A candidate blocked before READY or inference keeps P12
`Blocked`; target isolation alone is not offline-inference credit.

Repeat offline interfaces/routes, sensitive-environment, swap and throttling proof after all work.
Confirm model metadata still matches the receipt and scan runner-owned logs for prompt/output/
payload/credential/endpoint leakage. Issue per-candidate P states and cumulative receipt only after
Technical Lead, Internal Tester and User review. The receipt binds both the chronological Git commit
and the execution-surface digest; it never requires a later documentation-only commit to reuse the
same Git `HEAD`.

## 5. Command and evidence

```sh
python3 poc_llm/tools/run_gate1_pi_compat_v7.py \
  --packet-lock poc_llm/harness/gate1-pi-compat-lock-v7.json \
  --candidate-set poc_llm/fixtures/gate1/pi-compat-candidates-v7.json \
  --execution-sha <full-sha> \
  --run-id <G1-PI-COMPAT-007-UTC-ID> \
  --evidence-root /tmp/llm-poc-g1-pi-007/evidence
```

Raw receipts/stderr remain outside Git. Sanitized evidence stores identities, timings, terminal/
action disposition, LiteRT metrics, resource samples, calculations, cancel disposition, cleanup,
rebuild, P states and violations. It never stores prompt text, model text, payloads, binaries,
weights, credentials or endpoints.

Results use `PASS`, `FAIL`, `INCONCLUSIVE`, `Conditional escalation` or `Blocked` as allowed by each
item. A candidate is eligible only when P1/P7/P10A/P11/P12 are `PASS` and P6 is `PASS` or valid
`Conditional escalation` backed by P7 `PASS`. A valid candidate failure is not retried in this
revision; one identical retry is allowed only for reviewed infrastructure/evidence `INCONCLUSIVE`.
Packet, runner, schema or measurement failures are `INCONCLUSIVE`; only an authenticated candidate
observation that violates a frozen acceptance rule is `FAIL`.

## 6. Required Core disposition

After reviewer and User approval, Core is asked in one ACK to accept the cumulative boundary,
acknowledge the exact source SHA, supersede `006` for future execution and accept any explicitly
User-authorized pre-ACK evidence generated by this command. Gate 1 cannot be closed and P credit
cannot be final until that ACK binds the reviewed manifest.
