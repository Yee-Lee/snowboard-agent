# Current development status

## Active M4C implementation

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
