# HANDOFF-LLM-M4B-MVA-WORKSTATION-001 — Step 5 workstation continuation

- Date：2026-09-05
- Branch：`llm`
- Starting baseline：`b5ce101d1f75889bfcc1bf6f38ed563f59c2d9a1`
- Work / baseline / gate：`M4B-MVA` / `M4B-MVA-001` / `M4B-MVA-POC`
- Milestone state：`IN_PROGRESS / WORKSTATION CONTRACT AND RUNNER PREPARATION`
- Hardware state：`NOT USED IN THIS ROUND / NEW AUTHORIZATION REQUIRED`
- Purpose：preserve a complete, non-sensitive continuation record before workstation replacement

## 1. Authoritative inputs and verified identity

User confirmed on 2026-09-05 that `REQUEST-LLM-POC-M4B-MVA-MEASURE-001` was formally delivered.
The incoming target file is unchanged and has SHA-256
`5afb24e8ec7ad67853745ec290672c6b48a174819928936609556fefd184a2c2`.

The incoming document's relative Core links do not resolve in the `llm` checkout. Their exact
content was found and read without switching branches:

- frozen Core package source：`034a50f260e7434e586dddf64ef500da3b1b2b4e`；
- Core delivery-receipt source：`492f022c06962eb93b37fa0e93765f43690be1b2`；
- Core paths：`docs/implement/ch_m4b_llm_production.md`、`docs/milestones/M4B_MVA.md`、
  `docs/model_spec.md`、`docs/protocol.md`、`docs/reviews/IR_dev_M4B_III.md`、
  `docs/reviews/TR_spec_M4B_IV.md`；
- Core gate state：Steps 1–4 complete；Step 5 assigned to this POC；`M4B-MVA-POC` Open；
  Developer/Tester remain outside the gate until Designer Step 6 acceptance.

The LiteRT-LM API design was checked against official source commit
`924e79c91542761242244e4f1651851f822e4cbb`. That version exposes Conversation
`system_message`, constrained response format, `render_message_to_string`, `token_count`, async
generation and cancel. Official source warns that a cancelled Conversation is poisoned and must not
be reused. Real selected-wheel semantics still require Pi proof; source review is not hardware evidence.

## 2. Design disposition completed in this round

The old Gate 2B winner surface remains immutable provenance. M4B-MVA uses a separate profile and
does not rename or overwrite old P8/P9/P10B machine results.

| Concern | Frozen POC measurement disposition |
| --- | --- |
| Product context | one active Conversation per product session；normal turns reuse it；close before next session |
| Model output | exact compact `text/end`；no model-generated action/tool/next_perceptions |
| Reasoner boundary | deterministic projection to speak/listen or rest；capability drift fails closed |
| Prompt | tracked exact system and per-turn template bytes；each turn sends only the new perception |
| Tokens | 32 user-new admission separated from rendered/incremental/KV/output accounting；128 output reserve；1024 Engine KV |
| Pre-warm | only A/B variable is disposable public inference none/once；pre-warm Conversation is discarded |
| Recovery | no 8-attempt or 48 MiB trigger；natural memory trajectory and controlled replacement are separate |
| Memory | three fresh-child cycles ×20 two-turn sessions；fixed steady window sessions 11–20；MemAvailable primary |
| Quality | 12 operator-held sessions after freeze；manual rubric；no best-of/retry/LLM judge/raw answers in Git |
| Performance | TTFT, runtime TTC, caller TTC and audible onset are separate；no Audio proof means `llm_subsystem` only |

The selected adapter uses LiteRT-LM async generation so cancellation remains observable. It enforces
single flight, invokes native cancel at most once, retains the Conversation after a normal result,
retains it after pre-inference `INPUT_TOO_LARGE`, closes it on `CONTEXT_LIMIT`, and discards it after
cancel, timeout/native failure or invalid semantic output. Cleanup failure remains fatal and cannot
be represented as a clean session close.

## 3. Tracked implementation and documentation

### State, intake and handoff

- `docs/milestone/README.md`
- `docs/milestone/m4b_mva_product_parity.md`
- `docs/response/ACK-LLM-POC-M4B-MVA-MEASURE-001.md`
- `docs/response/HANDOFF-LLM-M4B-MVA-WORKSTATION-001.md`
- `docs/DOCUMENT_INDEX.md`
- `poc_llm/README.md`

### MVA contract surface

- `poc_llm/contracts/mva/system-prompt-v1.txt`
- `poc_llm/contracts/mva/user-turn-template-v1.txt`
- `poc_llm/contracts/mva/semantic-output-v1.schema.json`
- `poc_llm/contracts/mva/session-facts-v1.schema.json`
- `poc_llm/contracts/mva/wire-frame-v1.schema.json`
- `poc_llm/contracts/mva/mva-profile-001.json`
- `poc_llm/contracts/mva/machine-sample-v1.schema.json`
- `poc_llm/contracts/mva/manual-sample-v1.schema.json`
- `poc_llm/fixtures/mva/public-catalog-001.json`

### Harness, packet and tests

- `poc_llm/harness/mva_contract.py`
- `poc_llm/harness/mva_litert_backend.py`
- `poc_llm/tests/mva/M4B-MVA-POC-PACKET-001.md`
- `poc_llm/tests/mva/test_mva_contract.py`
- `poc_llm/tests/mva/test_mva_litert_backend.py`

The packet intentionally remains `execution snapshot draft`. No frozen execution SHA, run ID,
surface digest or Pi command is claimed before the controller/evidence writer/lock are complete.

## 4. Verification completed

Targeted MVA command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s poc_llm/tests/mva -p 'test_*.py' -v
```

Result：25 tests PASS. Coverage includes schema validity, strict `text/end`, removal of old envelope,
product-exact SessionFacts, `snowboard.llm/2`, Reasoner projection, two-turn Conversation reuse,
cross-session close, dirty-state discard, fatal cleanup, token admission, fixed A/B order, fixed
steady window, public/private catalog separation, disposable pre-warm, native failure sanitization,
single-flight and cancel-once behavior.

Full POC command:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 timeout 180 python3 -m pytest -p no:cacheprovider -q poc_llm/tests
```

Result：245 tests PASS in 104.87 seconds；one warning. The warning is emitted by the historical Gate 1
test `test_litert_lm_pi_async_child_adapter_v1.py::AsyncAdapterTests::test_cancel_once_discards_conversation_and_new_conversation_is_healthy`:
its test worker leaves an expected `BackendFailure("send_message_async")` unhandled in the thread.
It did not fail the suite and was not introduced by the MVA adapter. Preserve it as an explicit
pre-existing test-quality item; do not report the suite as warning-free.

`git diff --check` also passed. No model/runtime import, hardware access, benchmark, private prompt,
raw response, Audio sample, credential or endpoint was used.

## 5. Round-close `docs/pm_handoff/` audit

All four direct Income files are classified; none is moved or edited in this round:

| File | Classification / action |
| --- | --- |
| `DELIVERY-LLM-POC-M4B-CONTRACT-001.md` | governing original M4b contract；retain direct |
| `core_llm_m4b_tasks.md` | governing M4b/Core boundary；retain direct |
| `DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md` | immutable Gate 2A lock dependency at original path；retain direct |
| `REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md` | active unresolved MVA Step 5 Income；retain direct |

Historical completed ACK/review files remain under `docs/pm_handoff/history/`. The new MVA request
does not make the three older governing inputs completed or superseded.

## 6. Unfinished work and authorization boundaries

Every unfinished item at this checkpoint is listed below:

1. Implement the MVA controller, sanitized evidence writer and non-recursive surface lock; add
   failure-path tests and freeze exact case order, commands, timeouts, run IDs and raw path.
2. Run the selected LiteRT-LM 0.16.0 wheel API proof on Pi for system message, render/tokenize,
   token_count, constrained response, normal reuse, close and cancel/poison semantics.
3. Perform the frozen A/B timing matrix：six separate cold reboots in order N1/O1/N2/O2/N3/O3 and
   ten same-boot fresh Engine replacements in order N1/O1/.../N5/O5.
4. Select the baseline from valid samples without retuning, then run three fresh-child memory cycles
   of 20 complete two-turn sessions and three separate `capacity_test` recovery observations.
5. Determine whether exact Accepted Audio plus a verifiable same-timebase speech-end→meaningful
   audible-onset method is available. Until proven, scope remains `llm_subsystem` and audible latency
   must be `null`; M4 E2E remains Open.
6. Assign the independent manual evaluator/operator and controlled private presentation path for
   H01–H12 after prompt/schema freeze. Raw prompt, response and audio must remain outside Git.
7. Technical Lead must review identity, environment, packet, checksums, exit/cleanup, quality and
   performance before proposing a result.
8. User must review and approve all benchmark results and profile/candidate recommendations before
   publication. Core Designer alone can adopt the final profile and release `M4B-MVA-POC`.
9. No Pi work was authorized or attempted in this round. The user requested a separate notification
   when Pi is needed. The future request must include clean pushed SHA, surface digest, exact commands,
   six-reboot plan, duration, raw path, stop conditions and cleanup procedure.
10. This round authorizes the milestone commit and push requested for workstation transfer. It does
    not authorize Pi access, downloads/installation, network switching, artifact transfer, benchmark
    publication, cross-repo writes or Core product changes.

## 7. New workstation continuation procedure

1. Checkout branch `llm` at the pushed commit recorded in the final user handoff and verify
   `git status --short` is empty.
2. Follow repository `AGENTS.md`: read `.workstation-context.md` first or create a new ignored local
   file. Do not copy or infer the outgoing workstation's artifact, runner or Pi capabilities.
3. Read `docs/milestone/README.md`, this handoff, the active MVA milestone, intake ACK and incoming
   request. Read Core source by the exact commits above if product semantics need re-verification.
4. Re-run the 25 targeted MVA tests. Run the full 245-test suite before freezing the execution
   snapshot; preserve and report the known warning unless separately corrected and reviewed.
5. Continue only WP01 workstation work. Do not contact or power the Pi until the execution surface is
   complete, committed/pushed, and a new explicit Pi authorization request is granted.

No raw evidence exists for this round. No untracked dependency is required beyond repository files;
model/runtime artifacts and external runner availability must be rediscovered and recorded locally
on the new workstation.
