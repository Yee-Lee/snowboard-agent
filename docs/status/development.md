# Current development status

## Active ALPHA implementation

### Authority, value and scope

- Developer entry is Open in `docs/status/current.md`; authority is `docs/milestones/ALPHA.md`
  §§3–8 and `docs/test_spec/test_spec_ALPHA.md` §§3–7.
- Implement only the runner gaps for the four independent runs. Retain observations that identify
  stale work/owners, missing timing, failed recovery or unusable speech. No optimization is planned
  before a valid Pi baseline identifies a concrete bottleneck.
- Existing user changes to current status, the ALPHA Test Spec and its completed review are preserved.

### Work package estimate and planned affected paths

| Package | Estimate | Paths | Test IDs / verification |
| :--- | :--- | :--- | :--- |
| Production launcher driver and fixed PCM binding | 5 points | `scripts/alpha_product.py`, `tests/test_alpha_product.py` | All four ALPHA runs; real App supervision, production ASR/LLM/TTS/Audio, ordered Session fixtures |
| Timeout runner, public evidence and path oracles | 5 points | `scripts/run-alpha-pv.py`, `scripts/alpha_oracle.py`, `tests/test_alpha_pv_runner.py` | Lifecycle, Performance, Recovery and Quality; first failure, bounded cleanup, privacy-safe evidence |
| Run-specific observation and portable integration | 5 points | Above driver/tests; `src/` only if an actual product gap is demonstrated | Three Session barriers, P01–P05 causal timing, child kill/replacement, six once-only quality cases |

- Planned workstation verification: `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/test_alpha_product.py tests/test_alpha_pv_runner.py`; directly affected M4C/Reasoner tests;
  `PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not rpi'`; `git diff --check`.
- Planned Pi interface: `.venv/bin/python scripts/run-alpha-pv.py --run
  {lifecycle,performance,recovery,quality}` with explicit config, fixed fixture mapping, private/public
  output roots and finite watchdog. The interface is implemented; Pi results remain pending.
- USER confirmed on 2026-10-02 to follow the corrected documents: keep existing admission behavior,
  one Button per Session and the shorter fixed stimuli. Implement the runner without product API changes.
- USER subsequently explicitly requested commit/push after workstation testing, with Pi testing on
  the new workstation. This delivery overrides the usual pre-commit Pi order for this work package
  only; it is not Pi Verify, formal acceptance, or permission to amend a pushed candidate.

### Implementation result — 2026-10-02

- `scripts/run-alpha-pv.py` exposes exactly four independent runs, a finite invocation watchdog,
  first-failure retention, bounded cleanup of observed native child groups and sanitized evidence.
  Output directories are fresh and outside the repository; private answers/audio stay mode 0600.
- `scripts/alpha_product.py` invokes the existing `sbd.main.run_app` with its default production
  composition, validator, supervision and shutdown. Observation wrappers preserve existing calls;
  fixed PCM enters `AudioInput.frames`, while Button stimuli use the production GPIO button callback.
  ASR, LLM, TTS and Audio output execute normally; R1 input-limit speech cannot earn LLM path credit.
- Lifecycle executes three two-turn Sessions, observes each cleanup barrier, shuts down and restarts
  the launcher. A network namespace disables external networking; strace records network syscalls
  across both processes. One aggregate scan inspects the sanitized public report and actual emitted
  console/file logs from both launches, including Unicode JSON output and private credential matching
  in memory. Only aggregate counts are retained; short numeric answers do not match case-ID substrings.
- Performance records P01–P05 separately, including controller-clock startup/resource readiness,
  existing LLM timing, actual TTS batches/PCM/audio segments and token counts. It validates concurrent
  causal branches and retains invalid samples. Controlled PCM speech end is the last non-silent frame
  delivered to ASR. No optimization or numerical latency threshold is introduced before the Pi baseline.
- Recovery terminates the actual sole LLM child after safe-fragment admission, observes failure and
  barrier rejection, one replacement, a new complete Session and final release of product owners.
- Quality executes the six fixed cases once. Q05 closes through the existing short-press interruption
  after both voice turns complete; no third PCM or ASR terminal is admitted. A pending semantic card
  returns non-zero. Codex subsequently adjudicates the same private observation without another run;
  objective failure cannot be overridden. Public reasons are stable codes, never response excerpts.
- `IR_dev_ALPHA_I` is Resolved at `docs/reviews/history/IR_dev_ALPHA_I.md`; the corrected Button and
  fixture contracts are implemented. No product source or admission behavior was changed.

### Workstation verification

- Focused ALPHA and directly affected M4C/Reasoner command: **125 selected tests Pass**, exit 0.
- Final ALPHA driver/oracle/runner tests include actual Listen → Reasoner → StreamingSpeak → Audio
  controller integration for repeated Sessions and quality scheduling, actual subprocess watchdog and
  separate child-group cleanup, immutable PCM binding, concurrent timing, public privacy and same-run
  semantic adjudication. Latest affected-test result: **130 selected tests Pass**, exit 0.
- Earlier complete non-RPi runs: **1943 Pass** before the final additions, then **1940 Pass / 5 Fail**;
  failures were existing 3-second acceptance, 90-second nested suite, and 5-second child/App startup
  watchdogs. The exact five-test rerun retained three timeouts; a subsequent unchanged-limit rerun
  of those three passed (**3/3**, 30.48 s). Failure records are not relabeled as passing.
- Final complete non-RPi regression on the latest implementation:
  `PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not rpi' -o addopts=''`:
  **1948 Pass**, **35 deselected Pi tests**, exit 0, 220.29 s; zero Fail/Skip/XFail.
- `PYTHONPATH=src .venv/bin/python -m compileall -q src scripts tests`: Pass.
- Staged source/test whitespace checks and `scripts/privacy_gate.py scan-staged`: Pass.
  Markdown checks preserve the pre-existing intentional CommonMark hard break in `TR_spec_ALPHA_I`;
  that resolved review is not rewritten for whitespace-only cleanup.
- Actual workstation CLI invocation returns exit 2 with `INVALID / PI_TARGET_REQUIRED`; it cannot
  produce a Pi Pass on the x86_64 workstation.

### Pi execution interface and next action

Use the deployed production voice-only config with the existing M4 native runtime/model paths. Prepare
the fixed local PCM once before all four runs (or provide an already fixed recorded PCM mapping):

```bash
timeout 300s .venv/bin/python scripts/alpha_product.py \
  --config /path/to/product.local.yaml --prepare-fixtures /tmp/alpha-fixed-pcm
```

The preparation uses the offline production Matcha TTS, produces 16 kHz mono S16_LE WAV files plus
`fixtures.json`, and shares identical-question bindings. These are inputs, not acceptance observations.
Do not replace fixtures after the first valid run stimulus; all four runs use this same mapping.

```bash
.venv/bin/python scripts/run-alpha-pv.py --run lifecycle --run-id ALPHA-L01-DEV-01 \
  --config /path/to/product.local.yaml --fixtures /tmp/alpha-fixed-pcm/fixtures.json \
  --output /tmp/alpha-l01-dev-01 --watchdog 900 --network-launcher sudo-unshare
```

`sudo-unshare` uses noninteractive sudo to create the network namespace, then `setpriv` returns to
the invoking user's UID/GID/groups before strace and App execution; private artifacts remain readable
by that user. If the invoking account can
create a network namespace directly, use the default `--network-launcher unshare`. Missing privilege
or strace makes the run non-passing; it does not disable offline observation. Both child launches use
the same invocation watchdog. Every output directory must be new.

Performance, Recovery and Quality use the same command with `--run performance|recovery|quality`,
their own run ID and new output directory; they do not repeat lifecycle/network/privacy observations.
For Quality, Codex privately inspects `private/run-observation.json` on the Pi and supplies a local
JSON object keyed by the six case IDs, each with `disposition` and a sanitized `reason_code`. Finalize
that same run without executing product input again:

```bash
.venv/bin/python scripts/run-alpha-pv.py --run quality \
  --adjudicate /tmp/alpha-q-dev-01 --judgments /path/to/private/semantic-judgments.json
```

- Workstation development/testing is complete. Next owner: Developer/operator on the new workstation
  for isolated-checkout Pi development measurement, then final Pi Verify.
- No Pi run or ALPHA acceptance is claimed. Delivery follows USER's explicit pre-Pi commit/push
  instruction with approval of the complete message/file list; `current.md` remains Designer-owned.

## Last completed M4C implementation (retained record)

### Authority and scope

- Developer entry is Open by `docs/status/current.md`. Product authority is
  `docs/milestones/M4C.md`; executable authority is `docs/test_spec/test_spec_M4C.md`.
- The Pi catalog is exactly seven automatic sub-runs: S01, S02, S03, the three S04 variants and S05.
  S06/S07 are portable integration coverage. S08 adds no test or implementation. S09 is subsumed by
  S02, `M4C-SS-CTRL-001` C14/C15 and S04/ACTION. There is no human-result field.
- Assertions retain only stated product risks. Runtime scenarios do not calculate source, model, artifact,
  evidence or text digests. The content comparison below is a single candidate-transfer diagnostic.

### Final implementation result

- `scripts/run-m4c-pv.py` now contains only the seven authorized entries. Result validation forbids
  `user_result`; finalization requires one designated automatic Pass for every entry and rejects unknown,
  missing or duplicate active variants. Runner tests execute the exact seven-entry finalizer.
- `M4C-PI-S01/START_IDLE` is implemented in the exact-product Pi driver. It starts the real product graph,
  observes a bounded IDLE window, and requires no Session, no audio capture, no perception or error,
  Status `IDLE` (`待命`), empty Main and an open Display resource before orderly shutdown.
- S02 operator prompts are instructions only. Its THINK Main ledger now derives both expected values from
  the actual `PerceptionResult.text`; it does not compare ASR output with the prompted sentence. Terminal
  answer, synthesized speech and final Display answer equality remain unchanged and private text is not
  projected publicly.
- S06 cases are traced as `M4C-SS-OUTCOME-001/O08` and O09. O09 exposed retained StreamingSpeak inflight
  fragments after a TTS worker fault; the fault path now clears pending bytes, inflight fragments and PCM
  before publishing exactly one error. S07 is traced as `M4C-DISPLAY-001/D01` and proves one Display failure
  cannot interrupt two complete LLM→TTS→Audio turns or prevent final IDLE.
- The complete regression run exposed one pre-existing positional `LLMResponse` construction in the S04
  try-run. It is now keyword-only and passes the retained M4B structural anti-weakening gate; product behavior
  is unchanged.

### Verification result

- Workstation:
  - Focused runner, S02, S04, S06/S07 and M4C regression tests: Pass.
  - `PYTHONPATH=src xargs -a tests/m4c_portable_suite.txt .venv/bin/python -m pytest -q`:
    **529/529 Pass**.
  - `PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not rpi'`:
    **1890/1890 applicable Pass**, zero Skip/XFail.
  - `PYTHONPATH=src .venv/bin/python -m compileall -q src scripts tests` and
    `git diff --check`: Pass.
- Pi target, Python 3.13.5, isolated checkout `m4c-final-dev-20260926-A0dIDk`:
  - M4C portable catalog: **529/529 Pass**.
  - Complete non-RPi regression: **1890/1890 applicable Pass**, zero Skip/XFail.
  - `M4C-PI-S01/START_IDLE` attempt `M4C-S01-START-IDLE-20260926-02`: **Pass** in 5.05 s;
    public evidence reports `IDLE_READY`, no Conversation, no capture, Display open and Main empty.
    Evidence locator is `M4C-FINAL-DEV-20260926/M4C-PI-S01/M4C-S01-START-IDLE-20260926-02`.
- The final implementation-content comparison excludes `.git`, virtual environments, caches and this
  self-reporting status file. Workstation and Pi both produce SHA-256
  `d9f0c34aafe19be0ebf55b5b3ef22bf4ca6b0be1d591ab42b68e42b2dda2b9ee`; checksum-mode `rsync -anic`
  reports no file-content difference.

### Blocker and next action

- No implementation blocker remains. S02–S05 development hardware runs are already recorded by their
  existing scenario IDs; completed history is not repeated here.
- Next owner is Tester/Verify for the formal seven-sub-run M4C Pi PV and finalizer. The implementation is
  ready for one milestone commit proposal; commit and push still require explicit USER approval.
