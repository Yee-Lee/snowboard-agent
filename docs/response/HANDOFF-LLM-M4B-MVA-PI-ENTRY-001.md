# HANDOFF-LLM-M4B-MVA-PI-ENTRY-001 — workstation snapshot, stop before Pi

- Date: 2026-09-06
- Work / baseline / gate: M4B-MVA / M4B-MVA-001 / M4B-MVA-POC
- State: WORKSTATION SELF-TEST VERIFIED / READY FOR INTERNAL REVIEW / PI NOT AUTHORIZED
- Starting checkout: `llm`, `7a56137b7b2d65219ea4ff2065ab2773c179a0af`
- Execution SHA: full immutable commit accompanying this handoff in the final workstation report;
  pass that literal SHA to the runner, never branch HEAD. It remains outside the source manifest.
- Surface digest: `5a1c2ba19908c632bfeb1cd9d0e8f48beaa95e3563c470adcde8be750c95b5ca`
- Manifest: `poc_llm/harness/mva-surface-lock-v1.json` (canonical JSON digest, not file byte hash)
- Packet: [M4B-MVA-POC-PACKET-001](../../poc_llm/tests/mva/M4B-MVA-POC-PACKET-001.md)

## Authorization and contribution

User authorized restoration of the isolated workstation test environment and instructed
「同意。直接做到要連接pi之前」. This completes WP01 local implementation, verification and the
committed/pushed snapshot needed for later Pi entry. It does not authorize connecting to Pi,
power/network changes, reboot, artifact staging/install, benchmark/profile publication or external
delivery to Core. The older transfer-only authorization is not reused as Pi authorization.

This work advances the final M4B-MVA-POC checklist item: a reproducible product-parity result packet
whose exact source and observations can be reviewed by User and adopted by Designer. It establishes
the workstation execution surface only; it does not produce hardware results or release the gate.

## Implemented surface

- `mva_controller.py`: ordered public cases, normal same-session two-turn reuse, 20-session natural
  cycles, fixed 11–20 analysis, separate single-flight `capacity_test` replacement and owner barrier.
- `mva_worker.py` / `mva_process.py`: real isolated child/Engine, bounded private RPC, asynchronous
  native generation/cancel, independent watchdog, TERM/KILL/wait and process-group absence proof.
- `mva_identity.py`: initial model/wheel/runtime verification; same-install receipt checks avoid
  model rehash inside READY; runtime import origin and immutable profile parameters remain enforced.
- `mva_resources.py` / `mva_evidence.py`: fail-closed Pi probes, per-turn/session plus periodic
  trajectory, append-only/fsynced checkpoints and finalized schema-validated samples. Native stdout,
  stderr, exception text, prompt and answer have no evidence channel.
- `mva_surface.py` / `run_mva.py`: complete explicit inventory, local-import closure, non-recursive
  lock, clean exact-SHA/platform/offline gates, frozen case order and per-boot ledger/checksum checks.
- Backend now preserves tracked prompt/template newline bytes, owns its stream text extractor,
  performs pre-inference public tokenizer census and uses the same admission/cancel/close path for
  disposable prewarm. Historical adapters and Gate 1/2 evidence are unchanged.

The private POC RPC is not an implementation of or conformance claim for Core `snowboard.llm/2`.
Caller TTC includes open/close, IPC, parsing/validation and Reasoner projection; unsimulated Core
dispatch/event-loop/Audio costs are explicit exclusions. The selected baseline for natural memory
and controlled recovery remains the delivered no-prewarm baseline; no profile recommendation is
made. Audio digest and audible latency are null under `scope=llm_subsystem`.

## Workstation verification and environmental limits

Current machine: Darwin 24.5.0 / arm64 / Homebrew CPython 3.14.6. `.workstation-context.md` and
`.venv` are ignored local state. Test dependencies are pinned by
`poc_llm/requirements-mva-workstation.lock`, which includes the existing Gate 1 schema lock.
`pip check` reports no broken requirements. No native LLM artifact was downloaded or loaded.

Targeted command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s poc_llm/tests/mva -p 'test_*.py' -q
```

Result: **53 tests PASS**. This includes real worker subprocesses using fake runtime inputs, native
noise suppression, normal reuse and cancellation/fresh-session API proof, process timeout/reaping,
stalled-probe watchdog, memory/recovery failure paths, artifact metadata drift, schema hygiene,
newline identity, frozen-order enforcement and manifest tampering/omission/path rejection.
Process-group tests require local `ps`/`killpg`; they ran with sandbox escalation, only against
test-owned children. No test here is selected-Pi runtime proof or benchmark evidence.

Full command (activate the venv in PATH for historical subprocess tests):

```text
PATH="$PWD/.venv/bin:$PATH" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q --tb=no poc_llm/tests
```

| Source on this same workstation | Passed | Failed | Setup errors | Skipped | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unmodified handoff `7a56137b…` in isolated local clone | 224 | 6 | 9 | 6 | 2 |
| This final MVA implementation | 252 | 6 | 9 | 6 | 2 |

The same failed/error/skip identities occur in both runs. All 28 added tests pass. The suite is
**not globally green on macOS**; the previous workstation's 245 PASS is not inherited locally.

- Nine Gate 1 packet-v4 setup errors: test requires x86_64, this machine reports arm64.
- Two Gate 1 model-receipt failures and two Gate 2B cwd/runtime-origin failures: macOS temporary
  paths resolve through `/private`, while historical assertions require the unresolved spelling.
- One ARM64 RSS sampler and one P9 surrogate failure: tests depend on Linux `/proc`.
- Six original packet tests skip unsupported host architecture spelling.
- Warnings: existing Gate 1 unhandled cancellation test thread; Python 3.14 additionally reports
  the historical Gate 2B `return` inside `finally`. Both reproduce on the unchanged baseline.

No local Linux/x86 runner was found among installed runner commands. Those historical tests still
need their compatible environment for a full green run; MVA self-tests do not waive that limitation.
`git diff --check` passed. A workstation invocation of `api-proof` without authorization was rejected
with exit 2 / PREFLIGHT_BLOCKED before any runtime or hardware access.

## Round-close incoming-file audit

All direct `docs/pm_handoff/` files were classified. No incoming content is edited or moved:

| File | Disposition |
| --- | --- |
| `DELIVERY-LLM-POC-M4B-CONTRACT-001.md` | retain: governing original M4b contract |
| `core_llm_m4b_tasks.md` | retain: governing Core boundary |
| `DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md` | retain: locked dependency at original path |
| `REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md` | retain: active unresolved Step 5 request |
| `REQUEST-POC-LLM-PI-STORAGE-CURATION-001.md` | retain: newly arrived unresolved storage-curation request; original bytes preserved, Pi work not performed |

Completed historical incoming records remain in `history/`; `docs/DOCUMENT_INDEX.md` links this
new internal handoff and the new incoming request. No model, wheel, native binary, private
prompt/answer/audio payload or endpoint is added by the MVA implementation. The incoming document's
logical protected paths remain unchanged as governing input, not locally verified inventory.

## Remaining work at the Pi boundary

1. Explicit Pi access/power authorization, actual availability inventory, exact runtime/artifact
   paths and receipt location. Resolve the offline console/invocation method and persistent evidence
   storage before the first measurement; this runner never changes networking or installs artifacts.
2. Selected Pi runtime API proof and public-token census, followed by the frozen six-reboot cold
   matrix and ten same-boot replacements. No hardware status has been assigned in this round.
3. Three natural cycles (60 two-turn sessions) and three separate same-key recovery observations.
   Observe original stop rules, retain incomplete cases, and review cleanup before later cases.
4. Exact Accepted Audio/onset parity remains unproved; M4 E2E stays Open. It requires a separate
   accepted Audio scope and cannot be filled with LLM TTFT/TTC.
5. Assign the independent manual evaluator/operator and controlled private presentation method;
   H01–H12 must be created after freeze and evaluated once, with no private content in Git.
6. Technical Lead/internal review of identity, completeness, cleanup, quality and performance;
   User approval before any benchmark or profile publication; Designer adoption and explicit
   `gate released` remain required. No external review is impersonated by this self-test.
7. Historical platform-limited full-suite checks and the two existing warnings remain open as
   described above. Deferred P1.2 cold-start attribution and optional nonfinalist no-credit comparison
   remain informational backlog; they do not reopen the immutable original POC delivery.
8. Newly arrived `REQUEST-POC-LLM-PI-STORAGE-CURATION-001` remains unresolved. Its canonical-profile,
   result-index, worktree/storage inventory and exact cleanup-manifest work has not been executed.
   Core-reported Pi sizes/references are incoming claims, not observations from this workstation.
   Respect all protected holds; current User instruction still stops before Pi connection, and no
   permanent deletion is authorized. The MVA runner already references one external model/runtime
   root and does not copy the model into run directories; canonical deployment paths still require
   the separately scoped inventory and Core handoff.

Stop here before connecting to Pi. The packet fixes 23 public cases, six reboots and a conservative
16-hour maximum runner budget plus initial verification/boot/operator/cleanup time. Actual model,
runtime and Pi availability are unknown until authorized inventory; this is not an execution claim.
