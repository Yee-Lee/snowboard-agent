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

## M4a Gate 3 production integration (M4A-WP-09 to M4A-WP-13)

### Planning baseline

- **Authority:** `docs/implement/ch_m4a_audio_production.md`, `docs/model_spec.md`, `docs/protocol.md`, `docs/milestones/M4.md` and `docs/test_spec/test_spec_M4.md`.
- **Entry state:** Audio POC final reference is fixed at `audio_m4` / `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`; design and test-spec review are resolved. WP-01～08 are historical scaffold/runtime-closure work and do not satisfy the product Gate 3 locks or exact-SHA acceptance.
- **Estimation unit:** one ideal Developer day includes implementation, named automated tests, review fixes and local fast-loop execution; it excludes Tester-owned portable matrix, Raspberry Pi formal acceptance, evidence signing and USER-approved candidate commit time.
- **Total estimate:** **12.0 ideal Developer days**. WP-10 and WP-11 may proceed in parallel after WP-09's lock/parser and framed-child contract are stable. WP-12 starts after both adapter interfaces are executable; WP-13 can scaffold early but completes only after WP-10～12.
- **Scope boundary:** no public `ASRAdapter`, `TTSAdapter`, `Listen`, `Speak`, Audio HAL or factory signature changes; no real engine import in controller code; no artifact, wheel, model, raw audio or formal Tester evidence is committed.

### Work-package summary

| Work package | Estimate | Deliverable | Test-spec coverage | Dependency | Status |
| :--- | ---: | :--- | :--- | :--- | :--- |
| M4A-WP-09 | 2.5 days | Tracked product locks, notice inventory and fail-closed offline build/install/preflight CLI | `M4A-LOCK-001`, `M4A-PKG-001`; lock/config portion of `M4A-CFG-001` | Accepted Audio identity and controlled artifact metadata | Developer complete — Tester pending |
| M4A-WP-10 | 3.0 days | Common framed-child owner, whisper.cpp ASR adapter/supervisor and lifecycle recovery | `M4A-IPC-001`, `M4A-ASR-001`, `M4A-ASR-002`, `M4A-ASR-003`; ASR portion of `M4A-PRIV-001` | WP-09 lock parser and preflight contract | Developer complete — Tester pending |
| M4A-WP-11 | 2.5 days | Matcha worker/adapter, bounded PCM transport and AudioOutput-compatible stream | `M4A-TTS-001`, `M4A-TTS-002`; TTS portion of `M4A-PRIV-001` | WP-09 lock parser; WP-10 framed-child primitive | Developer complete — Tester pending |
| M4A-WP-12 | 2.0 days | Strict config, lazy factories, composition ownership and RM rebuild barrier wiring | `M4A-CFG-001`; recovery/composition portions of `M4A-ASR-003` and `M4A-TTS-002` | WP-10 and WP-11 adapter lifecycle complete | Developer complete — Tester pending |
| M4A-WP-13 | 2.0 days | Gate 3 target runner support, inheritance generator/template and offline/resource/privacy collection support | `M4A-OFF-001`, `M4A-RES-001`, `M4A-INH-001`; aggregate `M4A-PRIV-001` | WP-09～12 executable; Accepted M4b only for combined resource row | Developer complete — Tester pending |

### TR_dev_M4_I correction plan (M4A-WP-14 to M4A-WP-20)

| Work package | Estimate | Plan | Finding | Status |
| :--- | ---: | :--- | :--- | :--- |
| M4A-WP-14 | 0.75 day | Add bounded finite-input terminal silence and recoverable no-endpoint convergence without changing Audio Protocol v1. | `TRDEV-M4A-001` | Complete |
| M4A-WP-15 | 0.75 day | Replace buffered child stdin reads with one raw/unbuffered framing model and add fragmented/coalesced actual-process coverage. | `TRDEV-M4A-002` | Complete |
| M4A-WP-16 | 0.5 day | Enforce the single-thread OpenBLAS policy before controller native imports and in the formal candidate runner. | `TRDEV-M4A-003` | Complete |
| M4A-WP-17 | 0.5 day | Align the Pi actual-child cancellation case with deferred Level 1 observation, Level 2 destruction, rebuild and two-success recovery. | `TRDEV-M4A-004` | Complete |
| M4A-WP-18 | 0.5 day | Add a Developer-owned Pi pre-submit runbook and sanitized executable diagnostic for fresh device/product, offline ASR/TTS/ALSA and cleanup verification. | Process prevention requested after `TRDEV-M4A-001`～`004` | Complete |
| M4A-WP-19 | 0.25 day | Replace the nondeterministic CPython 3.11 asyncio transport-wait oracle with a bounded child-watcher return-code check, preserving every protocol assertion. | `TRDEV-M4A-002` re-verification regression | Complete |
| M4A-WP-20 | 0.5 day | Force-disable ONNX Runtime 1DS telemetry at the parent environment and both direct child entry boundaries; prove override-before-init and long-lived zero-network behavior. | `TRDEV-M4A-005` | Implementation complete — exact candidate pending |
| Developer re-verification | 0.5 day | Run named M4A regressions, candidate-runner tests and the primary-minor portable fast loop; record exact results in the review response. | All four findings | Complete |

The correction remains inside the approved public APIs and existing Audio Protocol v1 message set. Formal CPython 3.11/3.12/3.13 matrix execution and fresh Pi acceptance remain Tester-owned after a new USER-approved append-only candidate SHA is available.

Tester re-verification of candidate `ed1b2cf57581d48966a7dd6535c024ea51922b28`
exposed a CPython 3.11-only test-oracle race after the actual ASR child had exited
zero and been reaped. M4A-WP-19 changes only the final portable assertion to poll
the child-watcher-populated `Process.returncode` for the existing five-second
bound. The exact no-delay node passed 20/20 independent CPython 3.11 runs; the
four affected files passed 66 tests, and the complete M4A manifest passed all 167
tests on CPython 3.11.16, 3.12.3 and 3.13.15 with zero skip or xfail. A new
append-only candidate was created as
`7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d`. The candidate-runner regression
passed all 14 tests, and the repository non-RPi regression passed 451 tests with
28 target-only deselections.

Developer exact-candidate verification used a clean clone of `7aba0719…`.
Candidate gate run `m4a-7aba071-20260828-devp01` passed 167/167 tests on each of
CPython 3.11.16, 3.12.3 and 3.13.15. After rebooting the Pi, a fresh detached
checkout, product install and controller venv passed preflight. Real ASR completed
two nonempty turns plus bounded finite no-endpoint; real TTS completed ALSA,
deferred Level 2 destruction, rebuild and two recovery turns. Both traces had
zero IPv4/IPv6 calls, all cleanup deltas were zero, and the final target baseline
was clean. These results remain Developer verification, not Tester acceptance.

Formal target run `m4a-7aba071-20260829-pi01` later completed all seven product
cases but was correctly rejected because its full-tree trace contained 54
IPv4/IPv6 records from ONNX Runtime 1.29.0 1DS telemetry. M4A-WP-20 forces
`ORT_DISABLE_TELEMETRY=1` in the parent child environment and at ASR/TTS direct
entry boundaries before native initialization. Working-tree verification passed
73 affected tests, 14 candidate-runner tests, 171/171 M4a manifest tests on each
of CPython 3.11.16, 3.12.3 and 3.13.15, and 455 repository non-RPi tests with 28
target deselections. On Pi, a real Silero/ONNX session started from a conflicting
`ORT_DISABLE_TELEMETRY=0`, observed the forced `1`, remained alive for 40 seconds
and completed with zero IPv4/IPv6 trace records and no process residue. This is
working-tree diagnostic evidence only; exact-candidate and formal 20-turn reruns
remain required.

Developer fast-loop results on the designated local Python 3 minor:

- Focused ASR/IPC/TTS correction suite: `66 passed in 6.80s`, exit 0.
- Complete 13-ID M4A portable manifest: `167 passed in 9.92s`, exit 0; no fail, skip or xfail.
- Candidate-gate regression: `14 passed in 26.35s`, exit 0.
- Repository non-RPi regression: `449 passed, 2 skipped, 28 deselected in 70.23s`, exit 0. The two repository-level skips are outside the M4A formal manifest.
- Pi target suite collection: `7 tests collected in 0.36s`, exit 0.
- `py_compile` for every changed Python file and `git diff --check`: passed.

Developer Raspberry Pi working-tree diagnostic on 2026-08-28:

- Began after a device reboot with zero M4A processes, ALSA holders, ASR/TTS
  temp entries and formal-checkout tracked changes. The diagnostic used a new
  isolated checkout and loopback-only network namespaces; it is not formal
  acceptance and is not exact-candidate evidence because the fix is uncommitted.
- Fresh aarch64 whisper build passed with binary SHA-256
  `6aa73d996dfb03b12aabf5e706170301902ee9a3ceafa14573e7f269ec04cc26`;
  fresh product install passed with 8 wheels and product lock
  `21389a0fb6030a9ca74645003239119a9e299bd2719b98e2df15bc19a0c360d4`.
- Fresh controller-r2 closure preflight passed with manifest SHA-256
  `6bb24f9a0a2f2a66a522706b22222081fbf009b28c9dc0942a22d714114276f4`.
- Real ASR produced two nonempty results in 3883.509 ms and 3858.173 ms;
  finite no-endpoint converged recoverably in 135.881 ms. The complete process
  tree made zero IPv4/IPv6 calls and stopped with process/thread/fd/temp deltas 0.
- Real TTS wrote and drained 69,408 bytes through ALSA. The controller had one
  native thread after imports; deferred cancel escalated through Level 2,
  rebuilt and produced 69,460 / 69,350 bytes in two recovery syntheses. The
  complete process tree made zero IPv4/IPv6 calls and all cleanup deltas were 0.
- The repeatable procedure is
  `docs/runbooks/m4a_developer_pi_diagnostic.md`; the sanitized entry point is
  `scripts/m4a_developer_pi_check.py`. A USER-approved candidate must still be
  rerun from a clean exact SHA before Tester handoff.

### Developer WIP checkpoint — 2026-08-26

Work is intentionally paused for workstation shutdown. All changes remain uncommitted; no candidate SHA, Pi PASS, Tester handoff or milestone completion is claimed.

- WP-09～12 are implemented and have portable test coverage, but still require the final full regression and requirement-by-requirement audit. WP-13 is in progress: the portable manifest, target metrics/inheritance helpers and seven Pi-marked entries exist and collect, while formal Pi execution remains Tester-owned.
- The native whisper worker now reuses the Accepted Audio POC sources byte-for-byte instead of maintaining a Core rewrite. Locked SHA-256 values are `a1da74fa0f0a2f8cf94ea178c122b81eea6a4ee50275e9d8445710b19157c1a8` for `CMakeLists.txt` and `d3d0db1724b5882a358a6f6ae6edd08bc71d7ce9b0ce4b43781e72c8688a51dd` for `worker.cpp`.
- Last complete 13-ID portable run before the final adapter-cleanup patch: `123 passed in 4.57s`. The directly affected ASR/TTS subset was rerun after that patch: `19 passed`. Candidate-gate regression: `11 passed`. Pi suite collection: `7 collected`.
- The earlier repository `not rpi` run produced `399 passed, 2 skipped, 28 deselected, 2 failed`; both failures shared an unknown-driver exception compatibility issue. That issue was fixed and its focused config/M1 regression passed (`41 passed`), but the full repository run has not yet been repeated.
- An x86_64 native compile against the exact Accepted whisper.cpp `1.9.2` source succeeded before the worker source was replaced with the byte-identical Accepted POC version. Recompile and binary-manifest verification remain pending after this reuse correction.
- `git diff --check` was clean at this checkpoint. Existing unrelated PM handoff edits/untracked delivery files were not modified as part of M4A and must remain excluded from any future M4A commit.

Resume order:

1. Rebuild the exact reused native worker and verify the build-result v2 hashes/options.
2. Rerun the full 13-ID portable manifest and the complete repository `not rpi` regression.
3. Audit each M4A requirement/Test ID, especially target fault races, resource/privacy collection and product CLI failure paths.
4. Update the exact Tester handoff commands and evidence checklist; do not claim Pi acceptance from local collection.
5. Present the final diff, verification evidence and proposed commit contents to USER before any commit.

### M4A-WP-09 — Product identity and reproducible offline closure (2.5 days)

| Task | Estimate | Files / output | Done when |
| :--- | ---: | :--- | :--- |
| WP-09.1 Define versioned lock schemas and Accepted identities | 0.5 day | `requirements/m4a/audio-artifacts.json`, `vad-rpi-cp313.json`, `tts-rpi-cp313.json`, `whispercpp-build.json`; lock parser module | Required provenance, platform, interpreter, profile, size and SHA-256 fields are exact; missing/extra/mixed identity fails closed. |
| WP-09.2 Complete license/notice inventory | 0.25 day | `requirements/m4a/THIRD_PARTY_NOTICES.md` | Every runtime/artifact/dependency has a notice reference and Matcha/Vocos Accepted Risk is explicit. |
| WP-09.3 Implement product CLI | 1.0 day | `scripts/m4a_audio_product.py` | `build-whisper`, `install` and `preflight` accept caller-supplied inputs only, reject network/system-site/extra inputs, stage then atomically rename, and never overwrite an existing install. |
| WP-09.4 Add negative and clean-install regression | 0.75 day | `tests/test_m4a_lock_001.py`, `tests/test_m4a_pkg_001.py`, config cases in `tests/test_m4a_cfg_001.py` | Real assertions cover wrong checksum/version/SHA/interpreter/arch/profile, unsafe archive, incomplete notices, staging cleanup and exact inventory; no child or work artifact is created on rejection. |

WP-09 is complete only when a clean Git-external fixture can be installed and preflighted without network while the existing controller-r2 closure remains clearly non-candidate evidence.

### M4A-WP-10 — Framed child and production ASR (3.0 days)

| Task | Estimate | Files / output | Done when |
| :--- | ---: | :--- | :--- |
| WP-10.1 Implement bounded Audio Protocol v1 transport | 0.75 day | `src/sbd/adaptor/framed_child.py`; protocol doubles | Exact keys/bounds, fragmentation/coalescing, frame credit, request/sequence/hash validation, BUSY/EOF/late-terminal handling and process-group termination proof are asserted. |
| WP-10.2 Implement parent ASR owner | 0.75 day | `src/sbd/perception/listen/whispercpp/adapter.py` | Lifecycle is idempotent; 640-byte frame validation occurs before child I/O; endpoint stops frame demand; empty/error/cancel semantics and privacy contract match design. |
| WP-10.3 Implement isolated ASR supervisor | 0.75 day | `src/sbd/perception/listen/whispercpp/supervisor.py` | Silero request state resets per turn, pre/post padding is bounded, persistent whisper settings/identity are fixed, and all temporary WAV data is removed. |
| WP-10.4 Add lifecycle, recovery and Pi entry coverage | 0.75 day | `tests/test_m4a_ipc_001.py`, `tests/test_m4a_asr_001.py`, `tests/test_m4a_asr_002.py`, `tests/test_m4a_asr_003.py`, ASR cases in `tests/milestones/test_m4_local_voice.py` | Portable doubles prove all protocol and failure paths; Pi-marked entry proves real format/semantic smoke, persistence and same-baseline recovery without being run as Developer acceptance. |

WP-10 may reuse the common child primitive from WP-11, but engine semantics must remain in the ASR module. Any mismatch between `docs/protocol.md` and implement behavior opens `IR_dev_M4_*` rather than relaxing the wire schema.

### M4A-WP-11 — Production TTS and AudioOutput handoff (2.5 days)

| Task | Estimate | Files / output | Done when |
| :--- | ---: | :--- | :--- |
| WP-11.1 Implement parent TTS owner | 0.75 day | `src/sbd/action/speak/matcha/adapter.py` | First iteration acquires single-flight ownership; header/payload length and hash are checked; 16 kHz mono S16_LE chunks are yielded without resampling or padding. |
| WP-11.2 Implement isolated Matcha worker | 0.5 day | `src/sbd/action/speak/matcha/worker.py` | READY identity is exact; fixed voice/provider/profile is used; float-to-S16_LE conversion is deterministic; worker never opens Audio HAL or network. |
| WP-11.3 Prove Speak/AudioOutput completion and cleanup | 0.5 day | integration fixtures and Pi entry in `tests/milestones/test_m4_local_voice.py` | Completion occurs only after AudioOutput drains; output format is exact and actual-child success/error/timeout/cancel paths leave zero owned resource. |
| WP-11.4 Add named portable regressions | 0.75 day | `tests/test_m4a_tts_001.py`, `tests/test_m4a_tts_002.py`; TTS cases in `tests/test_m4a_priv_001.py` | Cooperative cancel, force-abort, SIGTERM/waitpid, controlled SIGKILL double, rebuild and next-success all contain real assertions. |

### M4A-WP-12 — Config, factory, composition and RM recovery (2.0 days)

| Task | Estimate | Files / output | Done when |
| :--- | ---: | :--- | :--- |
| WP-12.1 Extend strict real-driver config | 0.5 day | existing config module and example config | Exact real values and finite positive timeouts validate before factory/hardware; mock/null still require no artifact and preserve behavior. |
| WP-12.2 Add lazy factory branches | 0.25 day | existing ASR/TTS factories | Public signatures remain unchanged; only the selected real branch reads a lock and imports its adapter; native engines never import in controller. |
| WP-12.3 Wire single owner into composition and RM | 0.75 day | M4 composition/resource registration | `ResourceSpec.instance` and `recovery_hook` share one owner; real adapters are recoverable; stable keys and replacement barriers are exact; no public event/capability mutation occurs. |
| WP-12.4 Add config/composition recovery regression | 0.5 day | `tests/test_m4a_cfg_001.py`; extend named ASR/TTS failure tests | Invalid configuration creates no HAL/child/temp artifact; Level 2 blocks new work until same-baseline READY; mock/null and prior M1～M3 behavior regressions remain green. |

### M4A-WP-13 — Gate 3 execution and inheritance tooling (2.0 days)

| Task | Estimate | Files / output | Done when |
| :--- | ---: | :--- | :--- |
| WP-13.1 Add M4a target-suite orchestration | 0.75 day | candidate/acceptance runner support and `tests/milestones/test_m4_local_voice.py` | One fresh acceptance run can execute ASR, TTS, HAL, offline, privacy and Audio-only resource rows with bounded timeout and exact caller-supplied SHA; debug output cannot become formal PASS. |
| WP-13.2 Implement inheritance generator and resolver seam | 0.5 day | generator/template; `tests/test_m4a_inh_001.py` | P1～P12 and internal rows validate exact POC/product identity, content hash, Test ID/result locator and single product SHA; fast loop writes temp output only. |
| WP-13.3 Add offline/resource/privacy collectors | 0.5 day | runner helpers; `tests/test_m4a_off_001.py`, `tests/test_m4a_res_001.py`, `tests/test_m4a_priv_001.py` | Target entries expose zero-network-attempt, downloader, process-tree, P99, memory, cleanup, thermal and sanitized-output assertions without fabricating Pi results. |
| WP-13.4 Prepare Tester handoff manifest | 0.25 day | command/file/Test-ID checklist in this progress file | All 13 IDs map to executable tests and expected result-card fields; formal `inheritance.json` and result cards remain Tester-owned. |

### Execution order and merge checkpoints

1. **Checkpoint A — identity closure:** finish WP-09 and run `M4A-LOCK-001`, `M4A-PKG-001` and config-negative tests. No real child work starts until the lock parser is stable.
2. **Checkpoint B — protocol/lifecycle:** finish WP-10.1, then develop ASR and TTS streams against the same framed-child contract. Changes to framing require both ASR and TTS suites.
3. **Checkpoint C — real adapters:** finish WP-10 and WP-11 portable doubles plus Pi-marked entry points. Pi tests are collected but excluded from the Developer fast loop.
4. **Checkpoint D — product composition:** finish WP-12, then run affected M1～M3 config, worker, convergence, RM and composition regressions.
5. **Checkpoint E — handoff ready:** finish WP-13, run all named M4a portable tests and the repository `not rpi` suite on the designated primary Python minor. Record exact commands/results below; do not create formal evidence or claim target PASS.
6. **External candidate gates:** after Designer scope review and USER-approved provisional commit, Tester owns the 3.11/3.12/3.13 portable matrix, candidate freeze, Pi preflight/acceptance and final inheritance evidence. Any protected-input fix produces a new append-only candidate SHA.

### Test-file traceability and Developer fast loop

Each test-spec ID has an exact lowercase filename counterpart: `M4A-CFG-001` → `tests/test_m4a_cfg_001.py` through `M4A-INH-001` → `tests/test_m4a_inh_001.py`. Shared fixtures may live under `tests/fakes/`, but assertions remain in the named test module. Real Pi cases additionally live in `tests/milestones/test_m4_local_voice.py` with the `rpi` marker; this shared target entry does not replace the ID-specific portable module.

Planned bounded commands (results are recorded only after execution):

```bash
timeout 60s env PYTHONPATH=src python3 -m pytest -q \
  tests/test_m4a_cfg_001.py tests/test_m4a_lock_001.py tests/test_m4a_ipc_001.py \
  tests/test_m4a_asr_001.py tests/test_m4a_asr_002.py tests/test_m4a_asr_003.py
timeout 60s env PYTHONPATH=src python3 -m pytest -q \
  tests/test_m4a_tts_001.py tests/test_m4a_tts_002.py tests/test_m4a_priv_001.py \
  tests/test_m4a_off_001.py tests/test_m4a_res_001.py tests/test_m4a_pkg_001.py \
  tests/test_m4a_inh_001.py
timeout 120s env PYTHONPATH=src python3 -m pytest -q -m 'not rpi'
```

`M4A-OFF-001` and `M4A-RES-001` portable modules validate runner/collector behavior only; their product verdict requires the Tester-owned Pi acceptance command. The real M4a+M4b combined resource row remains `Pending` until an Accepted M4b input exists and must never be replaced by the surrogate result.

### Definition of Developer handoff ready

- WP-09～13 code and all 13 ID-named test modules are complete with real assertions; no skip/xfail is used to manufacture green status.
- All affected portable tests pass on the designated primary Python minor; Pi tests collect cleanly under `rpi` and have bounded, exact-SHA runner entry points.
- Product locks and notices are tracked, while binary/model/runtime payloads and generated formal evidence remain Git-external.
- Static inspection confirms controller modules do not import `onnxruntime`, `sherpa_onnx` or other candidate-native engines, and config rejection precedes hardware/child/temp creation.
- Recovery tests prove stable ASR/TTS keys, full process-group termination, cleanup and RM barrier reopening only after same-baseline READY.
- No formal M4a PASS, candidate freeze, combined M4a+M4b result or M4 Accepted claim is made. Remaining work is explicitly handed to Designer/Tester gates with the provisional candidate's immutable 40-character SHA.

### Developer handoff checkpoint — 2026-08-27

**Status: implementation and Developer verification complete; candidate commit,
portable matrix and Raspberry Pi acceptance remain pending.** No Raspberry Pi was
connected for this checkpoint, so the x86_64 compile and portable results below
must not be cited as aarch64 or hardware PASS.

Implemented closure highlights:

- The parent/controller keeps candidate-native imports out of Core. VAD and TTS
  run in separate exact CPython 3.13 aarch64 closures; whisper.cpp is a separate
  persistent native child. Child startup verifies every runtime distribution and
  exact READY identity.
- Audio Protocol v1 enforces bounded control/PCM, strict request/sequence/hash
  identity, single flight, BUSY/no queue, cooperative/deferred cancellation,
  EOF/late-terminal failure and whole-PGID TERM→KILL exit proof. RM tests use the
  real ASR/TTS owner and reopen the barrier only after same-baseline READY.
- ASR now keeps an exact 25-frame pre-speech ring and verifies the endpoint PCM
  checksum; TTS uses the fixed CPU/two-thread/sid-0/speed-1.0 profile and exact
  once-only S16_LE conversion.
- Matcha extraction is locked as 362 files with tree SHA-256
  `5e4f8625f9f7d62f9a410d33571ebcd1e3e5b8b0f43f1ebda23512a79e2f3319`.
  The product install schema is `sbd.m4a.product-install.v4` and checksum-binds
  the installed third-party notice inventory.
- Formal M4a acceptance injects the candidate SHA/run identity, finalizes metric
  drafts only after the entire suite passes, kills independent timeout descendants
  and uses `strace` to reject any `AF_INET`/`AF_INET6` syscall.

Developer evidence:

- 13-ID manifest: `160 passed in 8.25s`.
- Candidate-gate regression: `14 passed in 35.00s`, including exact M4a suite
  card finalization, zero-network trace parsing, attempted-network rejection and
  independent process-group timeout cleanup.
- Full repository `not rpi`: `442 passed, 2 skipped, 28 deselected in 103.43s`.
  Both skips are pre-existing M3 `samplerate` import guards; none of the 13 M4a
  modules contains skip or xfail.
- Pi collection: `7 tests collected`; no target test was executed locally.
- The Accepted Matcha archive was actually extracted and verified against the
  tracked 362-file tree lock. The exact whisper source/options/wrapper compiled
  on x86_64 to 2,206,696 bytes; this is compile evidence only. Pi must rebuild
  and record its own architecture-specific binary SHA-256.

#### Tester execution order

Use a clean checkout whose `HEAD` is the USER-approved provisional candidate.
Every `<...>` path below is Git-external. Run all product preparation and target
acceptance commands through an approved loopback-only namespace prefix such as
`<offline-exec>`; the invoked user must retain access to the checkout, ALSA and
controlled inputs. `strace` is mandatory on the Pi.

1. Build and install the Pi product from a fresh path:

```bash
<offline-exec> timeout 600s python3 scripts/m4a_audio_product.py build-whisper \
  --lock-root requirements/m4a \
  --source-archive <controlled-build-source>/whisper.cpp-v1.9.2.tar.gz \
  --build-root <new-build-staging> \
  --output <install-inputs>/m4a-whispercpp-worker \
  > <product-log-root>/build-result.json

<offline-exec> timeout 900s python3 scripts/m4a_audio_product.py install \
  --lock-root requirements/m4a --input-root <install-inputs> \
  --install-root <new-product-root> --python /usr/bin/python3.13 \
  > <product-log-root>/install-result.json

<offline-exec> timeout 120s python3 scripts/m4a_audio_product.py preflight \
  --lock-root requirements/m4a --install-root <new-product-root> \
  --core-repo <clean-checkout> --core-sha <candidate-sha> \
  --config <sanitized-real-audio-config> \
  > <product-log-root>/product-preflight.json
```

`<install-inputs>` must contain exactly the lock-listed VAD/TTS wheels, VAD/Whisper/
Matcha/Vocos artifacts and the newly generated worker plus its adjacent `.json`.
The config must bind those immutable install paths, select `whispercpp`,
`sherpa_matcha` and the Accepted ALSA profile. Confirm the preflight file is one
sanitized JSON object with `status=Pass`, candidate SHA, install schema v4,
Matcha tree SHA, notice SHA and `network_attempt_count=0`.

2. Produce the same-SHA portable matrix (normally CI supplies the three
interpreters):

```bash
python3.11 scripts/candidate_gate.py --repo <clean-checkout> portable \
  --candidate-sha <candidate-sha> --run-id <portable-run-id> --python 3.11 \
  --suite tests/m4a_portable_suite.txt --timeout-seconds 120 \
  --output <portable-root>/python-3.11
python3.12 scripts/candidate_gate.py --repo <clean-checkout> portable \
  --candidate-sha <candidate-sha> --run-id <portable-run-id> --python 3.12 \
  --suite tests/m4a_portable_suite.txt --timeout-seconds 120 \
  --output <portable-root>/python-3.12
python3.13 scripts/candidate_gate.py --repo <clean-checkout> portable \
  --candidate-sha <candidate-sha> --run-id <portable-run-id> --python 3.13 \
  --suite tests/m4a_portable_suite.txt --timeout-seconds 120 \
  --output <portable-root>/python-3.13
python3 scripts/candidate_gate.py --repo <clean-checkout> matrix \
  --candidate-sha <candidate-sha> --run-id <portable-run-id> \
  --input-root <portable-root> --output <portable-root>/matrix-index.json
```

3. Bind the product preflight JSON—not merely `install-manifest.json`—into the
candidate preflight, then execute one fresh formal target run:

```bash
python3 scripts/candidate_gate.py --repo <clean-checkout> preflight \
  --candidate-sha <candidate-sha> --run-id <pi-run-id> \
  --portable-index <portable-root>/matrix-index.json --runtime 3.13 \
  --hardware <hardware.json> --config <sanitized-real-audio-config> \
  --artifact-manifest <product-log-root>/product-preflight.json \
  --output <new-acceptance-root>

export SBD_M4A_TARGET_CONFIG=<sanitized-real-audio-config>
export SBD_M4A_ASR_PCM=<controlled-16k-mono-s16le-640-byte-aligned.pcm>
export SBD_M4A_INSTALL_ROOT=<new-product-root>
export SBD_M4A_PRODUCT_LOG_ROOT=<product-log-root>
export SBD_M4A_PRIVACY_SENTINEL=M4A_PRIVATE_CREDENTIAL_SENTINEL
export SBD_M4A_RESOURCE_TURNS=20

<offline-exec> timeout 900s python3 scripts/candidate_gate.py \
  --repo <clean-checkout> accept --candidate-sha <candidate-sha> \
  --run-id <pi-run-id> --preflight <new-acceptance-root>/preflight.json \
  --suite tests/milestones/test_m4_local_voice.py --timeout-seconds 600 \
  --output <new-acceptance-root>
```

The runner supplies `SBD_M4A_CANDIDATE_SHA`, acceptance run ID, runner preflight
and card root itself; do not pre-set or override them. Acceptance is valid only
when `result.json` and every finalized card use the same candidate/run, all seven
Pi tests pass with zero skip/xfail, `network_attempt_count=0`, cleanup deltas are
zero and privacy hits are zero. Generate formal `inheritance.json` only afterward
with `scripts/m4a_inheritance.py`; the Tester remains its sole formal writer.
The real M4a+M4b combined resource locator stays `Pending` until an Accepted M4b
input exists.

## Repository hygiene and PM-025 hardware diagnostic correction（2026-08-30）

USER已核准在M4b Tester建立新spec前先收斂目前`tests/`／`scripts/`邊界。本工作不改產品HAL、
M4a Accepted結論或M4b設計契約；它只修正test discovery污染、generated cache、工具分類與
`PM-OUT-260830-025`的診斷工具假綠燈風險。

| Work package | Estimate | Files / output | Done when |
| :--- | ---: | :--- | :--- |
| M4-HYG-01 Pytest authority | 0.25 day | `pyproject.toml`、移除重複`pytest.ini` | bare `pytest --collect-only`與明確`tests/`收集集合相同，不再收進`docs/outsource/**/poc_llm/tests` |
| M4-HYG-02 Scripts inventory | 0.25 day | `scripts/README.md`、M3 runner disposition、清除ignored cache | active candidate／M4a、diagnostic與legacy用途可定位；不移動current Test-ID files或改寫歷史evidence |
| PM-025-WP-01 Automated diagnostic | 0.75 day | `scripts/hw_diag/hw_diag.py` | Audio以已知tone acoustic loopback、Camera以payload/訊號、GPIO以chip/line transaction、Display以ABI/SPI transaction全自動判定；每步bounded且finally cleanup |
| PM-025-WP-02 Manual button separation | 0.25 day | `scripts/hw_diag/run_button.py` | conversation pin實體按壓有獨立bounded工具，不混入automated `hw_diag`結果 |
| PM-025-WP-03 Regression | 0.5 day | `tests/test_pm_025_hw_diag.py` | injected HAL證明success/failure、threshold、timeout、cleanup與GPIO edge；無Pi時不製造hardware PASS |

### Fixed diagnostic boundary

- `hw_diag`必須是zero-interaction；不得等待operator按button或以硬編碼人工`pass`形成結果。
- Audio不得以播放silence作喇叭PASS；使用固定頻率tone，並由產品mic回錄後比較baseline/tone能量。
  預設speaker tone長度固定為0.5秒。
- GPIO不得要求jumper或人工按鍵；自動結果只claim gpiochip access與設定中的conversation input line
  request／release，並明記無電氣刺激時不驗實體pin電位或button circuit。
- SSD1351無readback，故只能記`driver/ABI/SPI transaction PASS`與`visual panel unverified` limitation，
  不得把無exception改寫為肉眼顯示正常。
- `run_button.py`是獨立manual diagnostic；timeout或未按下即non-zero，不影響automated summary。
- Camera必須驗exact payload size／format與非單色luma range，並把本地artifact寫到Git外output directory。
- config由caller以`--config`明確提供；不得偷偷改device、format、ABI或pin。所有start成功的HAL都須在
  success、threshold failure、timeout、exception與cancellation路徑執行bounded stop／unregister。

### Planned verification

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pm_025_hw_diag.py
PYTHONPATH=src .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider
PYTHONPATH=src .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider tests
```

實機命令不需GPIO jumper或人工操作；Developer本機regression不宣稱Audio、OLED、Camera或GPIO
physical circuit PASS。

### Developer result（2026-08-30）

- `tests/test_pm_025_hw_diag.py`：`8 passed`；涵蓋tone成功／silence失敗、camera訊號與cancellation
  cleanup、GPIO input-line request／failure／release、display transaction failure，以及獨立bounded manual button。
- `tests/test_regression_guard.py`：`3 passed`。
- bare與明確`tests/`的`--collect-only` node集合完全相同；`docs/outsource/**/poc_llm/tests`不再被收集。
- `py_compile`及兩個CLI的`--help`均通過；`git diff --check`通過。
- 本機只有project不支援的Python 3.14.6；診斷性執行`-m 'not rpi'`結果為
  `442 passed, 15 failed, 28 deselected`。其中6筆為candidate gate正確拒絕`--python 3.14`，另9筆為
  macOS沒有Linux `/proc` process-group proof；不將此結果宣稱為portable gate PASS。
- Python 3.11／3.12／3.13 portable matrix仍須在對應環境執行。
- Pi diagnostic（非formal acceptance）：在remote source HEAD
  `237f404ce348bcd1f24b83f1dffd2c44c5127e3b`、Python 3.13.5與config SHA-256
  `4d16d1a37007fcf29daebaf2d39c6ce427597bede0ccb0c2c0a396e582b0c7f7`，由
  `scripts/hw_diag/run_diag.sh`隔離副本啟動後，Audio／Display transaction／Camera／GPIO line均PASS；
  summary位於Pi `/tmp/snowboard-hw-diag-live-20260830-2/summary.json`。最終Python script SHA-256
  `29b593495f60e2206af080b1198898bfc005a4c5df3762c7f72ecc2c87d4a76b`另以Audio-only重跑PASS，
  summary明記`tone_hz=440.0`、`tone_seconds=0.5`與`tone_gain_ratio=16.661`；沒有寫入formal evidence。

### Operator convenience refinement（2026-08-30）

依USER follow-up，Python工具集中至`scripts/hw_diag/`；`run_diag.sh`與新增的`run_button.sh`
在未傳`--config`時固定使用repo root的`config.m3.local.yaml`。因此Pi日常操作分別為
`scripts/hw_diag/run_diag.sh`與`scripts/hw_diag/run_button.sh`，不再要求operator填寫參數。

## M4b Local LLM production integration（2026-08-30）

### Entry and delivery boundary

- **Entry state:** `IR_review_M4B_I`與`TR_spec_M4B_I`均為`Resolved`；Designer已標記
  `DEVELOPMENT READY`。Accepted input固定為Gemma candidate
  `CAND-LRT-G4E2B-MOBILE-R1`與pairing`litert-lm-v0.16.0-pi-g2b-r5`。
- **Implementation authority:** `docs/implement/ch_m4b_llm_production.md`、`docs/protocol.md` §4、
  `docs/test_spec/test_spec_M4.md`的15個M4B Test ID。
- **Non-claim:** Developer fast loop不構成portable matrix、Pi target PASS、candidate freeze或M4b Accepted；
  POC P9/P10B machine FAIL與User waiver保持分欄。

### Work packages

| Work package | Estimate | Files / symbols | Dependency | Affected tests | Exit evidence | Status |
| :--- | ---: | :--- | :--- | :--- | :--- | :--- |
| M4B-WP-01 Structured protocol seam | 1.5 days | `src/sbd/cognition/llm.py` structured values；`src/sbd/cognition/llm_child_protocol.py` exact codec/state；`tests/fakes/m4b_llm_child.py` deterministic child double | Resolved design/test-spec reviews | `M4B-IPC-001`、`M4B-RDY-001` portable；existing Reasoner/contract regressions | exact frame/key/type/boundary/state tests PASS；controller不import real runtime | Developer complete — Tester pending |
| M4B-WP-02 Strict config / lock / factory / package | 2.0 days | config models/defaults/validation；`src/sbd/cognition/litert_lm/` factory/lock；`requirements/m4b/`；`scripts/m4b_llm_product.py` | WP-01 public types；exact CPython closure disposition | `M4B-CFG-001`、`M4B-LOCK-001`、`M4B-PKG-001` portable | valid exact config/lock accepted；negative matrix zero side effect；offline inventory deterministic | Developer complete — target-ready；Pi preflight pending candidate |
| M4B-WP-03 Parent lifecycle / recovery | 3.0 days | `litert_lm/adapter.py`、resource sampler、RecoveryTicket ports、process-group cleanup | WP-01 codec；WP-02 verified identity | `M4B-RDY-001`、`M4B-CAN-001`、`M4B-REC-001`；affected M4a lifecycle | startup/pre-warm/admission/cancel/recycle/replacement deterministic cases PASS；zero orphan | Developer complete — Tester/Pi pending |
| M4B-WP-04 Isolated winner worker | 2.5 days | `litert_lm/worker.py`、renderer/tokenizer/constrained-output binding、fresh Conversation | WP-02 runtime closure；WP-03 parent lifecycle | `M4B-GEN-001`、`M4B-OUT-001`、`M4B-HIST-001` focused portable/Pi | preflight identity and controlled target smoke executable；no controller native import | Developer complete — target-ready；Pi execution pending frozen candidate |
| M4B-WP-05 Reasoner / composition / fatal supervision | 2.5 days | `reasoner.py`、`prompt_builder.py`、M4 composition、RM hook/barrier、main `rm.wait_fatal()` | WP-03 lifecycle；WP-04 structured generation | `M4B-P5-001`、`M4B-PRIV-001`、CAN/REC regression | P5/fatal split、same-owner recovery、next-success、privacy and no-request fatal monitor PASS | Developer complete — Tester pending |
| M4B-WP-06 Candidate / resource / inheritance closure | 3.0 days | `tests/m4b_portable_suite.txt`、canonical M4 target suite、resource collector/verifier、M4b inheritance generator | WP-01～05 executable；complete product closure | `M4B-OFF-001`、`M4B-RES-001`、`M4B-INH-001`；full affected suite | primary-minor Developer fast loop PASS；formal target fields/cards and inheritance inputs ready for Tester | Developer tooling complete — candidate-ready；snapshot／Pi gates pending |

### Implementation order and gates

1. WP-01先固定public structured values與pure codec；不等待real LiteRT-LM或Pi，且不得以double宣稱target PASS。
2. WP-02在任何native import、spawn、workdir、sampler或RM registration前完成config／lock fail-closed。
3. WP-03只透過窄ports取得recovery control；replacement在`INFERENCE_READY`前不得admit。
4. WP-04僅於isolated child lazy import selected runtime；每次GENERATE建立fresh Conversation。
5. WP-05保留Reasoner對product schema與P5的authority，child不得執行tool handler。
6. WP-06保留完整20-session samples與r14 4/64 gates；正式evidence由Tester對USER核准candidate SHA產生。

### Developer fast-loop commands

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_m4b_ipc_001.py tests/test_m4b_rdy_001.py
PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_contracts.py tests/test_config.py tests/test_m4a_ipc_001.py
```

每個WP完成時更新本表status與實跑輸出；不得以code review或`assert True`替代執行證據。

### WP-01～06 Developer completion evidence（2026-08-30）

- 新增structured `LLMGenerationMetrics`／`LLMGeneration`／resource/recovery ports；Protocol的
  `generate()`已改為`ReasoningInput`；raw-text bridge已移除，production與Mock皆使用required structured metrics。
- 新增pure `snowboard.llm/1` codec：canonical GENERATE、CANCEL、READY六欄identity、typed terminal、
  finite metric/token bounds、16 KiB framing、sanitized failure及child-side exact-schema parser。
- deterministic child double驗四個non-READY state zero-write、single-flight總GENERATE write=1、monotonic
  request identity、typed single CANCEL與next admission。
- Strict config、Accepted product lock、14-file LiteRT wheel inventory、notice inventory、offline install/preflight WIP、
  parent process-group owner、resource sampler、8/48/768 recycle、fresh-Conversation worker與dynamic response schema均已落地。
- Reasoner已分離P5與fatal contract；real LLM在composition以同一instance作`ResourceSpec.instance`／recovery hook，
  `ResourceManager.wait_fatal()`由main常駐監督background recovery failure。
- `tests/m4b_portable_suite.txt`收集163項（含15個M4B modules與受影響M4a regression）並實跑全部PASS；
  canonical Pi suite collect 8個test functions且包含M4b exact-product 11-card collector，但未在本機執行Pi測項。
- Primary local CPython 3.12完整`-m 'not rpi' tests`收集575項並實跑exit 0；此結果是Developer fast loop，
  不取代Tester對candidate SHA的3.11／3.12／3.13正式matrix。
- Tracked sanitized r14 20-sample vector重現`5.900893 / 131.578 / 0.101957 / 32.750`四個凍結輸出；
  inheritance generator拒絕mixed SHA、self-row、unresolved proof與waiver改寫。
- `py_compile`與`git diff --check`通過；這些portable結果不消除product closure缺口。
- **Blocking:** implement/test spec要求tracked manifest列出isolated interpreter的relative path／size／digest，
  但Accepted authority只固定Debian 13 aarch64與CPython 3.13，未固定patch/package revision、source
  artifact、stdlib/native dependency closure或deterministic inventory。標準`venv --copies`仍引用host
  stdlib，generated inventory也不能替代tracked authority。`IR_dev_M4B_I`已請Designer決定self-contained
  runtime artifact或明定target ABI boundary；在Resolved前，WP-02／04 target readiness／06 handoff及
  provisional candidate均不得宣稱complete。

### Workstation shutdown checkpoint（2026-08-30）

- USER要求暫停；Developer已停止編輯、測試與任何長時間程序，未建立commit或candidate SHA。
- `IR_dev_M4B_I`已由Developer接受Designer選定的Option 2 target ABI boundary、標記`Resolved`，並移至
  `docs/reviews/history/IR_dev_M4B_I.md`。原self-contained CPython closure blocker因此解除。
- 新契約固定target-owned `/usr/bin/python3.13`、CPython 3.13.5、SOABI／MULTIARCH／stdlib boundary、
  五個Debian套件同版tuple、base executable digest與glibc identity；product-owned tracked manifest只保留
  14-file LiteRT-LM payload。
- **尚未完成：** `scripts/m4b_llm_product.py`仍只驗CPython 3.13 minor，尚未實作canonical
  `PythonABIAttestation`、install inventory attestation、preflight／acceptance drift compare、exact package及
  isolation negative matrix；tracked manifest仍寫`python.version=3.13`且其lock digest尚未重算。
- **Tester dependency：** `TR_spec_M4B_II.md`仍為`Open`，`M4B-LOCK-001`／`M4B-PKG-001`仍保留舊
  interpreter-in-manifest oracle；在其Resolved前不得宣稱WP-02／04／06 target-ready或建立provisional candidate。
- `tests/m4b_target_cases.py`有一批尚未驗證的WIP：20-session marker／intent／cancel／P5/cards已接線，
  但recycle後prewarm擷取、per-generation PSS delta、swap／OOM／thermal／throttled與cleanup仍須改成真實量測；
  檔內暫存的無效recovery yield及fabricated zero evidence必須移除。
- 停機前最後已知綠燈仍是先前的163項M4B portable與575項`not rpi`；上述target-runner與ABI裁決後的
  最新WIP尚未重跑，不能引用舊結果證明目前worktree通過。
- **安全接續點：** 先完成Option 2 ABI capture/compare與LOCK/PKG tests，再修正target resource evidence，
  依序跑focused tests、163項M4B portable、全體`not rpi` regression及`git diff --check`。

### Workstation resume and Developer closure（2026-08-30）

- 已依Option 2完成canonical `PythonABIAttestation`：固定`/usr/bin/python3.13`、CPython 3.13.5、
  SOABI／MULTIARCH／64-bit little-endian／stdlib與`lib-dynload`、glibc、base executable digest及五個
  Debian package同版tuple；install、preflight與acceptance均重算並拒絕任一drift。
- product-owned runtime manifest已收斂為exact 14-file LiteRT-LM payload；`--copies --without-pip` venv、
  protected install inventory、stdlib positive／system-user third-party negative isolation、native pre-import
  authentication及strict product config逐欄cross-check均已有portable positive／negative assertions。
- canonical Pi runner已移除fabricated cleanup/resource evidence，改採20個real kernel/process samples、
  exact owner PID分帳、swap／OOM／thermal／throttle與cleanup delta；固定attempt 8／16 recycle、三個generation
  baseline／pre-warm／ticket及r14 4/64 gates。Pi suite以`-m rpi --collect-only`收集8項，未在本機執行。
- cooperative cancel現只在typed terminal、worker join及terminal resource/recycle cleanup均完成後return；
  並行及terminal後才進入的`abort()`共用同一convergence event、只送一次CANCEL，且同child下一輪成功。
- 最新Developer fast loop：M4B portable `215/215 PASS`；repository `-m 'not rpi' tests`
  `633/633 PASS`；M4B Python modules `py_compile`與`git diff --check`均PASS。這些測試使用double，沒有讀取
  工作站另一路徑的Gemma／LiteRT-LM POC artifacts。
- **Remaining external gate:** `TR_spec_M4B_II.md`仍為Tester-owned `Open`，故WP-02／04／06不得標
  target-ready、不得建立provisional candidate或執行Pi Gate 3。其Resolved後仍須USER核准candidate commit，
  再由Tester對同一SHA完成三minor portable matrix與Pi target acceptance；目前不宣稱M4b Accepted。

### Pre-shutdown completion-audit checkpoint（2026-08-30）

- USER要求工作站關機前停在可恢復段落；Developer已停止長時間驗證，不執行Pi、不建立commit／candidate，
  且不留下刻意啟動的背景程序。
- 本輪完成production lifecycle hardening：Reasoner timeout保留operation ownership；cancel／force-abort／rebuild
  均等待或強制收斂並清理child；replacement前重新驗證runtime與config；cleanup residue改為fail closed。
- worker補齊request identity連續性、pre-bind CANCEL、native cancel failure與result/error race的typed terminal；
  interpreter建立、ABI probe與worker啟動均明確使用`-B`，避免runtime inventory受bytecode污染。
- output schema authority已收斂：child只限制tool arguments為object，sealed ToolRegistry／Reasoner負責完整schema；
  target evidence改驗exact thread／fd identities、privacy markers與artifact digest、真實resource上限及固定card欄位。
- inheritance與candidate gate已拒絕area證據缺漏、duplicate／wrong-scope proof及結構正確但語意不足的card；
  formal runner固定candidate `src`與preflight config path／digest，避免繼承外部`PYTHONPATH`或config。
- 上述各區focused tests均已通過；先前完整M4B portable `215/215`與non-Pi `633/633`曾通過，但在最後一批
  audit patches及`PytestUnhandledThreadExceptionWarning`升級為error後尚未完整重跑，因此列為stale evidence，
  不用來宣稱目前worktree完成。
- **恢復後必做：** `py_compile`與`git diff --check`；完整M4B portable；完整`-m 'not rpi'`；Pi suite
  `--collect-only`確認exact 8項；再整理Developer handoff。`TR_spec_M4B_II.md`仍為Tester-owned `Open`，
  在Resolved前不得宣稱WP-02／04／06 target-ready、建立provisional candidate或執行Pi Gate 3。

### Post-restart Developer verification and handoff（2026-08-31）

- 以`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`隔離工作站全域ROS pytest plugins後，完整M4B portable suite
  實跑`231/231 PASS`；新增的thread warning policy會將`PytestUnhandledThreadExceptionWarning`升級為error。
- 完整repository `-m 'not rpi' tests`實跑`651/651 PASS`；collection為`651/680`、另有29項Pi測試。
  M4 canonical Pi入口`tests/milestones/test_m4_local_voice.py -m rpi --collect-only`精確收集8項，包含唯一
  `test_m4b_exact_product_gate3_cards`，但依role gate未在本機執行Pi或載入Gemma／LiteRT-LM artifacts。
- M4B／LiteRT-LM Python source與test以AST parse完成syntax check；`git diff --check`通過。程式與測試中未找到
  TODO、FIXME、NotImplemented、placeholder、WIP或`assert True`殘留；target evidence中的`fabricated`只存在於
  必須拒絕fabricated counter的negative test名稱。
- WP-01～06的Developer-owned source、portable tests、candidate/evidence tooling與受影響M4a regressions均已完成；
  本輪沒有發現需再修改的Developer code。此結論只代表implementation handoff ready，不代表target PASS或M4b Accepted。
- **External gate remains:** `docs/reviews/TR_spec_M4B_II.md`仍為Tester-owned `Open`；而
  `docs/test_spec/test_spec_M4.md`的`M4B-LOCK-001` negative matrix仍保留舊的
  `interpreter/distribution/native file relative path/size/digest` runtime-closure oracle，尚未依Option 2改為
  product-owned 14-file payload＋target ABI attestation。Tester修訂、Designer複審並Resolved前，不得將
  WP-02／04／06標target-ready、建立provisional candidate、執行Pi Gate 3或宣稱M4b Accepted。
- 未建立commit或candidate SHA。外部gate解除後，下一步是先向USER展示完整commit title／body／files並取得
  明確同意，再建立provisional candidate，交Tester執行CPython 3.11／3.12／3.13 matrix與同SHA Pi acceptance。

### Resolved-ABI Developer re-entry and candidate readiness（2026-08-31）

- Designer已將`TR_spec_M4B_II`標記`Resolved`並歸檔至`docs/reviews/history/`；WP-02／04／06的
  test-spec blocker解除，Developer重新依核准的`M4B-LOCK-001`／`M4B-PKG-001`逐項audit實作與tests。
- audit補強target venv probe：除stdlib與product site外，dynamic stdlib extension亦必須位於
  `/usr/lib/python3.13/lib-dynload`；wrong implementation／abiflags／base digest／sys.version／glibc、
  missing／non-regular／symlink／non-root base及wrong package revision均有table-driven fail-closed assertion。
- product preflight validator改為exact 14-key sanitized schema，固定lock／14-file manifest／model／config digest，
  拒絕unknown／absolute private metadata；M4B-PKG draft card只允許四個核准evidence欄位，不再攜帶
  session／generation等未規範資料。Target card仍在acceptance finalization後繼承runner公共欄位。
- install regression直接捕捉唯一`/usr/bin/python3.13 -I -B -m venv --copies --without-pip`命令與clean env，
  證明無apt／pip installer／download路徑，且tracked 14-file manifest不被target bytes改寫。
- 最新Developer fast loop：LOCK／PKG／candidate focused suite PASS；M4B portable `242/242 PASS`；repository
  `-m 'not rpi' tests` `663/663 PASS`（collection `663/692`、另29項Pi）；canonical M4 Pi suite
  `-m rpi --collect-only`精確8項；M4B source/tests AST parse及`git diff --check` PASS。
- **Candidate-ready, not Accepted:** 尚未建立commit／push／candidate SHA，也未執行Pi。下一步須依workflow
  展示完整candidate commit title／body／files並取得USER明確確認，再push同一immutable SHA，交Tester執行
  三minor portable sign-off；Designer freeze後才在Pi以新run ID執行preflight／acceptance。

### Provisional candidate Pi packaging correction（2026-08-31）

- USER核准的provisional candidate `60cb29de9640996f0253f7d4292a1c33929bcd29`已push至`origin/core`；同SHA
  portable matrix在CPython 3.11／3.12／3.13各為`242/242 PASS`。Pi repository亦已fast-forward至同一SHA、
  protected paths clean，固定target為CPython 3.13.5／Debian 13／aarch64，canonical M4 Pi suite收集8項。
- Git外LiteRT-LM 0.16.0 aarch64 wheel與Gemma 4 E2B model已在Pi取得並以tracked size／SHA-256完整核對；
  winner product config亦精確符合`c4557b...`。首次real installer diagnostic因標準`venv --without-pip`預先
  建立空`site-packages`而fail closed，揭露portable fake runner未模擬的real-target gap。
- installer現只允許既有、非symlink且為空的site-packages，並拒絕non-empty／symlink destination；target
  stdlib probe改用Pi實際dynamic `_bz2` extension，而非在Debian build中屬built-in且無`__file__`的`_json`。
  ABI probe亦分開驗base platstdlib `/usr/lib/python3.13`與isolated venv platstdlib位於product root。
- 修正版以Pi `/tmp` standalone diagnostic執行，不修改candidate checkout：real install `Pass`（14 runtime
  files、23 inventory files），後續model／config／ABI／inventory／platform／candidate read-only product
  preflight亦`Pass`。該diagnostic不構成formal preflight、Tester PASS或candidate freeze。
- Post-correction Developer regression：M4B portable `246/246 PASS`；repository `-m 'not rpi' tests`
  `667/667 PASS`（collection `667/696`、另29項Pi）；修正檔`py_compile`與`git diff --check`亦PASS。
- 上述修改觸及installer與portable regression，依append-only規則使`60cb29d...`不再可送正式target gate；
  完整portable／non-Pi regression通過並取得USER commit確認後，必須建立新candidate SHA、重新執行三minor
  matrix，再交Designer review／freeze。禁止amend、rebase、reset或force-push改寫舊candidate。
