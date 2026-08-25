# Developer Progress — M4

## M4a generic scaffold (M4A-WP-01 to M4A-WP-04)

| Work package | Estimate | Plan | Status |
| :--- | :--- | :--- | :--- |
| M4A-WP-01 | 0.25 day | Add null ASR/TTS adapters and engine-agnostic factories without importing a real engine. | Complete |
| M4A-WP-02 | 0.25 day | Extend ASR/TTS configuration placeholders, validation, defaults, and the example configuration. | Complete |
| M4A-WP-03 | 0.25 day | Wire the factories into the existing composition and register M4a resource timeout defaults. | Complete |
| M4A-WP-04 | 0.5 day | Add ASR-NULL, TTS-NULL, and CFG regression tests; run the affected portable suite. | Complete |

### M4a scope and constraints

- Authority: `docs/implement/ch_m4a_generic_scaffold.md` and `DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003` §4.
- This work supplies only the `mock` / `null` generic scaffold. It must not add a real ASR/TTS import, model path, production dependency, or reference to a POC branch head.
- Existing `Listen`, `Speak`, and mock-adapter behavior remain unchanged. A candidate-specific adapter requires the later M2B provisional-selection ACK.

### M4a developer verification

- `PYTHONPATH=src python3 -m pytest -q tests/test_m4a_generic_scaffold.py tests/test_config.py tests/test_m2_wrk_001_002_004.py` → `31 passed`.
- `PYTHONPATH=src python3 -m pytest -q -m 'not rpi'` → `275 passed, 2 skipped, 21 deselected`.
- `python3 -m py_compile` passed for all changed Python modules.

### M4a handoff status

- **Core generic scaffold: Complete.** `NullASRAdapter` and `NullTTSAdapter`, their config-driven factories, engine-agnostic schema placeholders, resource timeouts, and the designated regression coverage are complete.
- **Candidate-specific audio integration: Blocked by the planned external gate.** Audio POC must first return the M2A baseline and M2B optimization result, followed by a Core M2B provisional-selection ACK. Until then, Core must not select or import a real engine, model, voice, or production dependency.
- **Next Developer entry criterion:** receive the M2B provisional-selection ACK and the exact candidate recipe; then implement the candidate-specific adapters, provisional configuration/dependency integration, and the corresponding Core delta tests.
- This is a dependency boundary, not an implementation defect. It does not claim M4a Gate 3, Tester PASS, candidate freeze, or milestone acceptance.

## M4a runtime closure (M4A-WP-05 to M4A-WP-08)

| Work package | Estimate | Plan | Status |
| :--- | :--- | :--- | :--- |
| M4A-WP-05 | 0.25 day | Inventory the Pi Core, VAD, TTS, and whisper runtimes against `REQ-AUDIO-M4-RUNTIME-CLOSURE-002`. | Complete |
| M4A-WP-06 | 0.5 day | Define a versioned offline wheel inventory and isolated controller-runtime manifest without mixing VAD/TTS native stacks. | Complete |
| M4A-WP-07 | 0.5 day | Implement a fail-closed preflight for interpreter, venv isolation, Core SHA, wheel checksums, and Core Audio HAL imports. | Complete |
| M4A-WP-08 | 0.25 day | Run a clean Pi reproduction and return the required closure evidence for Audio POC review. | Complete — Audio POC review pending |

### M4a runtime closure inventory (Pi, 2026-08-25)

- Pi hostname `snowboard` runs Python `3.13.5`. The deployed Core checkout is at `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`, with an untracked `config.m3.local.yaml`; it must not be overwritten during closure work.
- Its existing `.venv` is invalid for this request because `include-system-site-packages = true`. It currently resolves `pyalsaaudio==0.11.0`, `samplerate==0.2.4`, `PyYAML==6.0.2`, and `numpy==2.4.2`, but not from an isolated closure.
- Audio POC already has isolated VAD and TTS venvs, but their NumPy/native stacks differ. The Core controller closure must remain separate, be checksum-locked, and reject system-package resolution.
- Controlled closure root: `/home/yee/.local/share/sbd/m4a-runtime-closure-002/` on the Pi. It holds separate controller-r2, VAD, and TTS wheel inventories, manifests, fresh isolated venvs, and clean-reproduction logs; it is intentionally Git-external.
- Controller-r2 uses the request's `numpy==2.4.2`; VAD and TTS retain their separately locked `numpy==2.5.2`. All three `--no-index` installs and fail-closed preflights passed. The controller result is tied only to the currently deployed M3 SHA, not an M4a candidate.

## Candidate gate reform (WP-PROC-01 to WP-PROC-03)

| Work package | Estimate | Plan | Status |
| :--- | :--- | :--- | :--- |
| WP-PROC-01 | 0.75 day | Keep a minimal candidate-gate CLI for portable, matrix, preflight, acceptance, and unrestricted diagnostic runs. | Complete |
| WP-PROC-02 | 0.5 day | Keep focused regressions for exact SHA, protected paths, scope split, matrix completeness, timeout, checksum recording, and run-output reuse. | Complete |
| WP-PROC-03 | 0.25 day | Run the CPython 3.11/3.12/3.13 matrix only for candidate branches or manual dispatch. | Complete |
| Developer verification | 0.5 day | Run the focused gate suite on the designated local Python minor and report the handoff commands. | Complete with environment note |

## Scope and constraints

- Authority: `PM-OUT-260818-018-m4-portable-gate-cost-correction` and `docs/runbooks/candidate_hardware_gate.md`.
- This delivery changes only development/acceptance tooling, tests, metadata, and CI; it does not alter production M3 behavior or claim a frozen candidate, Pi PASS, or Tester sign-off.
- Candidate identity is always caller-supplied. The runner fails before a suite or hardware operation when SHA, protected paths, matrix, runtime/checksum input, or run isolation is invalid; manual evidence remains in the milestone report/card rather than this runner.
- WP-PROC-04 remains owned by Tester and is not performed by this Developer fast loop.

## Developer verification

- `tests/test_candidate_gate.py` covers only the retained checks; manual handshake, debug FAIL-bundle authorization, multi-layer checksum-chain and six command-level dry-run cases were removed.
- `PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py` → `10 passed` on the designated local Python minor.
- `python3 -m py_compile scripts/candidate_gate.py` → passed.
- Available non-RPi regression was split to stay within the local command bound: core/M1 groups `166 passed`; M2 groups `36 passed`; M3 group `34 passed, 20 deselected` with one environment-only failure in `test_m3_aud_001` because `samplerate==0.2.4` is absent. The current local Python has no `pip` module, so that declared dev dependency cannot be installed here. CI installs `.[dev]` before executing the 3.11/3.12/3.13 matrix.
