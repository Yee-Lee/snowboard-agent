---
requestor: "Tester"
owner: "Developer"
status: "Rejected"
---

# TR_dev_M4_I — M4A Gate 3 candidate rejection

## Review identity

- Candidate: `306dbc96585d1eef55ba0c6380e2eeceaa2057fc`
- Portable run: `m4a-306dbc9-20260828-p01`
- Pi acceptance run: `m4a-306dbc9-20260828-pi01`
- Formal result: **Fail** — suite timeout after 600 seconds
- Sanitized evidence summary: `docs/outsource/evidence/M4A-TESTER-306DBC9-20260828/README.md`

## Blocking findings

### TRDEV-M4A-001 — Finite ASR input without endpoint waits forever

- **Test IDs / contract:** `M4A-ASR-001`, `M4A-ASR-002`, `M4A-ASR-003`; `ch_m4a_audio_production.md` §5.2–§5.3 requires bounded endpoint/transcription, no-speech convergence and cleanup.
- **Reproduction:** run the formal `candidate_gate.py accept` command from the evidence summary with the only naturally 640-byte-aligned approved fixture (`asr-pause-040`). The suite remains on `test_m4a_asr_001_and_002_real_persistent_two_turns` until the 600-second runner timeout. A direct `StreamingEndpoint + Silero` diagnostic proves this fixture processes 195 frames, reaches probability `0.9971`, remains triggered at EOF and never forms `speech_end` or `ENDPOINT`.
- **Evidence:** no JUnit, result card or `result.json` was produced. The runner wrote `accept-failure.json` with `reason="suite timeout after 600.0 seconds"`. Candidate descendants were terminated, but one per-process ASR temp directory remained.
- **Root cause:** after the finite frame iterator is exhausted, `WhisperCppASRAdapter.transcribe()` receives `(None, None)` from `_next_frame_or_event()` and enters an unbounded terminal receive loop. The supervisor has no EOF/END transition and emits no terminal when Silero has not declared an endpoint.
- **Expected / actual:** finite input must produce a bounded transcript, no-speech/error result, or bounded recovery; actual behavior waits indefinitely and relies on the outer runner to kill it.
- **Preferred correction:** add a contract-aligned, bounded end-of-input/no-endpoint transition across the adapter and supervisor. If this requires a new wire operation, revise `docs/protocol.md` through the design workflow rather than adding an undocumented message. Preserve endpoint checksum, cancellation and cleanup semantics.
- **Minimum re-verification:** portable EOF/no-endpoint regression plus Pi real-VAD runs proving both a nonempty fixed-fixture result and a bounded no-endpoint result; then rerun the full three-version matrix and fresh Pi acceptance.

### TRDEV-M4A-002 — Buffered control coalescing deadlocks the real ASR child

- **Test IDs / contract:** `M4A-IPC-001`, `M4A-ASR-001`, `M4A-OFF-001`; Audio Protocol v1 must tolerate fragmented/coalesced control and payload traffic, and real inference must make zero network attempts.
- **Reproduction:** run the real adapter with the POC M4 `asr-pause-038` fixture padded only to a complete 20 ms frame. Without an artificial send delay, a 30-second IPC wrapper receives only `READY`: no `FRAME_ACCEPTED`, `ENDPOINT` or terminal event, and the adapter remains `BUSY`. Add a diagnostic-only 100 ms wait after sending `BEGIN`; the unchanged candidate then returns `ENDPOINT` at frame 102 and a nonempty `RESULT` in under five seconds.
- **Evidence:** the no-delay trace records 27 IPv4/IPv6 calls in 30 seconds; the delayed successful run records zero. The 600-second formal stalled run records 72 lines, including DNS connects to `192.168.0.1:53` returning `ENETUNREACH`. Standalone Silero streaming, direct real whisper transcription, and the delayed end-to-end adapter path all complete with zero network calls. This proves that whisper inference alone is not sufficient to trigger the attempts; the exact userspace caller in the stalled integration path is not yet attributed by the syscall-only trace.
- **Root cause:** `supervisor.py` combines `select.select()` on the stdin file descriptor with buffered `sys.stdin.buffer.readline()` / `read()`. Reading `BEGIN` can prefetch the immediately coalesced `FRAME` into Python's buffer; the underlying fd then appears not readable, so the loop never calls `read_control()` for that buffered frame. Portable `ScriptedChild` tests do not exercise this OS-pipe condition.
- **Expected / actual:** expected exact protocol behavior for coalesced BEGIN/FRAME traffic and zero network attempts; actual real child deadlocks before acknowledging frame zero. The prolonged stalled process also violates the formal offline trace gate.
- **Preferred correction:** make supervisor framing use a single buffering model that never gates already-buffered data on fd readiness—for example an unbuffered/raw fd parser or an explicit internal byte buffer. Do not add timing sleeps to production. Add an actual-process regression that writes coalesced BEGIN + FRAME bytes and proves `FRAME_ACCEPTED`/`ENDPOINT`/terminal behavior.
- **Minimum re-verification:** no-delay real adapter run returns nonempty `RESULT`, fragmented/coalesced actual-process regressions pass, and the fresh formal trace has `network_attempt_count=0` through a complete offline ASR/TTS/HAL session. If the network attempt persists after the IPC repair, capture PID/TID-to-executable identity and a userspace stack before assigning it to NSS, VAD or whisper.

### TRDEV-M4A-003 — Production launch lacks the required native thread policy

- **Test ID / contract:** `M4A-TTS-001`; successful synthesis and AudioOutput drain must leave process/thread/fd/temp cleanup deltas at zero.
- **Reproduction:** run `test_m4a_tts_001_real_pcm_and_audio_output_drain` on Pi after ensuring `/tmp/sbd-m4a-tts` is writable by the operator.
- **Evidence:** under the default product environment, real Matcha synthesis and ALSA drain complete with approximately 69 KB PCM, then the cleanup assertion fails with `orphan_processes=0`, `thread_leaks=3`, `fd_leaks=0`, `temp_leaks=0` immediately and after one second. `/proc` shows three new native tasks named `python`, while `threading.enumerate()` contains only `MainThread`. A dependency-only probe reproduces exactly three tasks when importing NumPy 2.4.2 + samplerate 0.2.4. With `OPENBLAS_NUM_THREADS=1` set before process startup, the unchanged candidate's complete real `M4A-TTS-001` node passes in 5.43 seconds and leaves no candidate-specific process; its card records 69,454 PCM bytes.
- **Expected / actual:** expected all cleanup deltas zero; actual three persistent native threads remain in the Core process.
- **Preferred correction:** establish a production-owned native thread policy before the controller imports NumPy/samplerate; the confirmed minimal setting is `OPENBLAS_NUM_THREADS=1`. Apply it to the real product/service and formal runner entry, not only an ad-hoc debug shell. Keep the accepted cleanup assertion unchanged.
- **Minimum re-verification:** make the policy part of the production-owned launch path, then repeat the real TTS→ALSA success case without an ad-hoc shell override and assert all four cleanup counters are zero after drain/stop.

### TRDEV-M4A-004 — Pi cancellation test does not follow deferred→Level 2 contract

- **Test ID / contract:** `M4A-TTS-002`; actual-child cancel/timeout must not fake success and must converge through cancellation or Level 2 recovery.
- **Reproduction:** run `test_m4a_tts_002_actual_process_group_destroy_and_recovery` on Pi.
- **Evidence:** the child returns `CANCEL_DEFERRED`, but the target test then unconditionally waits for `CANCELLED` within the configured 30-second child-ready timeout; `asyncio.wait_for()` raises `TimeoutError`. `worker.py` can emit `CANCELLED` only after the uninterruptible native synthesis future finishes. An external contract-aligned Pi diagnostic keeps the deferred operation pending for a bounded Level 1 observation, then proves `force_abort()` reports the stable TTS key, reaches `DESTROYED`, rebuilds, completes two subsequent real syntheses and stops with all four cleanup deltas at zero; the case passes in 6.11 seconds.
- **Expected / actual:** `ch_m4a_audio_production.md` §4.3 explicitly permits unsupported cooperative cancellation to remain pending until Level 1 expires and Level 2 performs process-group termination. The current target test instead requires cooperative completion and fails before exercising the allowed escalation/rebuild path.
- **Preferred correction:** revise the actual-child target case to accept `CANCEL_DEFERRED`, prove the Level 1 operation remains pending rather than reporting success, then invoke `force_abort()`, verify TERM/KILL/waitpid and cleanup, rebuild the same baseline and complete the required subsequent syntheses. Do not weaken the final recovery or cleanup assertions.
- **Minimum re-verification:** actual Matcha error, cancel, timeout, TERM/KILL proof, rebuild READY and two subsequent successful syntheses, with zero cleanup deltas.

## Advisory

### TRDEV-M4A-A01 — Target was contaminated by earlier runs

Before this run, the Pi contained two older ASR process groups and several stale ASR temp directories pointing to a different checkout/install root. `/tmp/sbd-m4a-tts` was an empty `root:root 755` directory and initially blocked the `yee` operator; its ownership was restored after confirming it was empty and unused. These are not used as candidate findings, but the next formal run must begin from a clean target or a documented operator cleanup/reboot. Candidate-specific processes from the timed-out formal run are currently zero.

## Re-verification gate

Because protected product/test inputs require correction, create a new append-only candidate SHA after USER commit approval. Do not reuse, amend or replace the rejected SHA. Tester will rerun the complete CPython 3.11/3.12/3.13 portable matrix, product build/install/preflight and one fresh Pi acceptance run. Debug output from this round cannot be promoted into the new formal result.

## Developer response — Revised

### TRDEV-M4A-001 — Correction implemented; formal re-verification pending

- **Root cause:** the parent treated finite iterator exhaustion as capture completion even though Audio Protocol v1 has no end-input terminal. It then waited indefinitely for a supervisor terminal that could not exist while Silero remained triggered.
- **Correction:** `WhisperCppASRAdapter` now sends at most 100 credit-governed 20 ms silence frames after finite EOF. This permits the fixed 500 ms end-silence plus 600 ms post-padding to form a normal endpoint. If no endpoint forms within the exact two-second bound, the parent sends the existing `CANCEL`; `CANCELLED` returns the child to READY and raises a recoverable `AdapterRejected`. No public API or wire operation changed.
- **Regression:** `tests/test_m4a_asr_001.py` proves a finite source reaches a nonempty result through terminal silence and proves an exact flush-bound no-endpoint case sends one CANCEL, returns READY and performs no force termination. Both cases additionally run the parent adapter against the actual supervisor control loop in an OS child process, with bounded completion and clean shutdown/workdir removal.

### TRDEV-M4A-002 — Correction implemented; formal re-verification pending

- **Root cause:** `select()` observed the OS stdin fd while `sys.stdin.buffer.readline()` could prefetch a following coalesced FRAME into Python's private buffer. The fd then appeared empty and the supervisor stopped consuming the already-buffered command.
- **Correction:** ASR supervisor control headers and payloads now read exclusively from the raw `FileIO` beneath stdin. The TTS worker uses the same single buffering policy for control input, preventing the equivalent GENERATE/CANCEL race. No timing sleep was added to product code.
- **Regression:** `tests/test_m4a_ipc_001.py` launches the real supervisor control loop as an OS child process. Parameterized fragmented and no-delay coalesced BEGIN+FRAME writes both receive matching `FRAME_ACCEPTED`, reach `ENDPOINT`, receive a nonempty `RESULT`, acknowledge shutdown and exit zero.

### TRDEV-M4A-003 — Correction implemented; formal re-verification pending

- **Root cause:** the controller and formal runner inherited an arbitrary host `OPENBLAS_NUM_THREADS`, so importing NumPy/samplerate could create three persistent native tasks not visible to `threading.enumerate()`.
- **Correction:** `sbd.main` enforces `OPENBLAS_NUM_THREADS=1` before importing any project module that can lazily reach NumPy/samplerate. `candidate_gate.py` applies the same production policy to every pytest subprocess before formal target-suite import.
- **Regression:** `tests/test_m4a_tts_001.py` starts a clean interpreter with a conflicting value and proves importing the product entrypoint changes it to exactly `1`; `tests/test_candidate_gate.py` proves an acceptance subprocess receives exactly `1`. The Pi cleanup assertion remains unchanged.

### TRDEV-M4A-004 — Correction implemented; formal re-verification pending

- **Root cause:** the Pi case interpreted `CANCEL_DEFERRED` as requiring a later cooperative `CANCELLED`, contrary to the allowed Level 1 pending to Level 2 destruction path.
- **Correction:** the actual-child test now observes that no terminal arrives during the configured Level 1 interval, cancels only its pending observer, invokes `force_abort()`, verifies the stable TTS key and `DESTROYED`, rebuilds the same baseline, completes two real syntheses, stops, and retains all four zero-cleanup assertions.
- **Target status:** the Developer working-tree Pi diagnostic executed the real deferred→Level 2→rebuild path and completed two recovery syntheses with cleanup zero. This is diagnostic evidence only; Tester must repeat the formal target node on a clean exact candidate.

### Developer verification

- `timeout 60s env PYTHONPATH=src python3 -m pytest -q tests/test_m4a_asr_001.py tests/test_m4a_ipc_001.py tests/test_m4a_tts_001.py tests/test_m4a_tts_002.py` → `66 passed in 6.80s`, exit 0.
- `timeout 120s env PYTHONPATH=src python3 -m pytest -q -m 'not rpi' $(tr '\n' ' ' < tests/m4a_portable_suite.txt)` → `167 passed in 9.92s`, exit 0; zero fail/skip/xfail.
- `timeout 120s env PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py` → `14 passed in 26.35s`, exit 0.
- `timeout 180s env PYTHONPATH=src python3 -m pytest -q -m 'not rpi'` → `449 passed, 2 skipped, 28 deselected in 70.23s`, exit 0. The two repository-level skips are outside the formal M4A manifest.
- `env PYTHONPATH=src python3 -m pytest --collect-only -q -m rpi tests/milestones/test_m4_local_voice.py` → `7 tests collected in 0.36s`, exit 0.
- Changed-file `py_compile` and `git diff --check` both passed.

### Developer Raspberry Pi diagnostic — 2026-08-28

- The Pi was rebooted first. The post-boot baseline had zero M4A processes,
  ALSA holders and ASR/TTS temp entries; the formal checkout had no tracked
  changes. All audio commands ran in loopback-only network namespaces.
- A fresh aarch64 whisper build passed with SHA-256
  `6aa73d996dfb03b12aabf5e706170301902ee9a3ceafa14573e7f269ec04cc26`.
  Fresh product installation passed with eight wheels and product lock
  `21389a0fb6030a9ca74645003239119a9e299bd2719b98e2df15bc19a0c360d4`.
  The fresh controller-r2 closure passed manifest/checksum/import preflight.
- Real ASR returned two nonempty results in 3883.509 / 3858.173 ms. A finite
  no-endpoint input converged to the recoverable bounded result in 135.881 ms.
  The complete trace contained zero IPv4/IPv6 calls; process, native-thread,
  fd and temp cleanup deltas were all zero.
- Real TTS wrote and drained 69,408 bytes through ALSA. The controller contained
  one native thread after audio-stack import. Deferred cancellation remained
  pending through Level 1, Level 2 destroyed the child, rebuild succeeded and
  two subsequent syntheses produced 69,460 / 69,350 bytes. The complete trace
  contained zero IPv4/IPv6 calls and every cleanup delta was zero.
- These results used an isolated checkout with the uncommitted working-tree
  patch, so their status is **Developer Diagnostic Pass**, not exact-candidate
  verification or Tester acceptance. The repeatable preparation, runtime and
  failure rules are now recorded in
  `docs/runbooks/m4a_developer_pi_diagnostic.md`, backed by the sanitized
  `scripts/m4a_developer_pi_check.py` entry point.

### Candidate handoff

Protected source, test and runner inputs changed, so rejected SHA `306dbc96585d1eef55ba0c6380e2eeceaa2057fc` is not reused or rewritten. A new append-only provisional candidate commit remains pending the final exact commit confirmation. After its full SHA exists, Developer must first repeat the Pi diagnostic from that clean exact SHA; only then is it handed to Tester for the complete CPython 3.11/3.12/3.13 portable matrix and one fresh Pi build/install/preflight/acceptance run. No Developer diagnostic output is formal evidence.

## Tester re-verification — Rejected

### Candidate and gate result

- New append-only candidate: `ed1b2cf57581d48966a7dd6535c024ea51922b28`.
- Tester portable run: `m4a-ed1b2cf-20260828-p02`.
- CPython 3.11.16: **Fail** — 166 passed, 1 failed, 0 skipped/xfailed.
- CPython 3.12.3 and 3.13.15: Pass — 167 passed each, 0 failed/skipped/xfailed.
- Candidate-runner regression: 14 passed. Adjacent `not rpi` regression: 451 passed, 28 deselected.
- Formal matrix is **Fail**, so target preflight and acceptance were correctly not started.
- The Pi was rebooted as requested. Boot ID `85777d3e-7dda-4ff5-8190-cc03901959f6` had zero candidate processes, ALSA holders and ASR/TTS temp entries; this clean target remains unused by acceptance.
- Sanitized evidence summary: `docs/outsource/evidence/M4A-TESTER-ED1B2CF-20260828/README.md`.

### TRDEV-M4A-001, TRDEV-M4A-003 and TRDEV-M4A-004

The new portable regressions for finite-input convergence, production OpenBLAS policy and deferred cancellation all pass on the three supported Python minors. Their required real-device dispositions remain Pending because the portable entry gate failed; they are not reopened or promoted to Pass.

### TRDEV-M4A-002 — Rejected: Python 3.11 actual-process exit oracle is nondeterministic

- **Contract / Test ID:** `M4A-IPC-001`; `docs/protocol.md` §2.2 and `test_spec_M4.md` require `READY → SHUTDOWN → SHUTDOWN_ACK → STOPPED` plus bounded parent waitpid. The portable matrix requires zero Fail on CPython 3.11/3.12/3.13.
- **Formal reproduction:** with host `PYTHONPATH` removed and third-party pytest autoload disabled, run candidate `ed1b2cf57581d48966a7dd6535c024ea51922b28` through `candidate_gate.py portable --python 3.11 --suite tests/m4a_portable_suite.txt --timeout-seconds 120`. `test_m4a_ipc_001_actual_asr_process_handles_coalesced_and_fragmented_input[False]` receives `FRAME_ACCEPTED`, `ENDPOINT`, nonempty `RESULT` and `SHUTDOWN_ACK`, then `asyncio.wait_for(process.wait(), timeout=5)` raises `TimeoutError`.
- **Repeatability:** the unchanged node passes twice and fails on the third independent run. This is a reproducible false-green risk, not a one-off result eligible for retry promotion. Under `strace` it passes 5/5, confirming timing sensitivity.
- **Root cause evidence:** a Tester-only wrapper around `asyncio.subprocess.Process.wait()` records, at cancellation after 5.007 seconds, `process.returncode=0` and `/proc/<pid>` absent. The child was already reaped; Python 3.11's asyncio subprocess transport waiter remained pending on its pipe callbacks. Replacing `wait()` with bounded `communicate()` still fails on iteration 9, so pipe draining does not resolve this runtime behavior.
- **Expected / actual:** expected a deterministic portable proof that the real child is reaped within the bound; actual test intermittently fails after proving the child already exited zero. This prevents a valid three-version matrix and therefore blocks Pi acceptance.
- **Exact correction:** keep every protocol assertion unchanged, but replace the final `Process.wait()` oracle with a bounded poll of `process.returncode`. Asyncio sets that property only after its child watcher processes waitpid, so this proves reaping without depending on the delayed transport waiter. The following disposable patch passes the failing node 20/20 on CPython 3.11, all four affected files (`66 passed`) and the complete M4A manifest (`167 passed`):

```diff
@@
-            assert await asyncio.wait_for(process.wait(), timeout=5) == 0
+            deadline = asyncio.get_running_loop().time() + 5
+            while (
+                process.returncode is None
+                and asyncio.get_running_loop().time() < deadline
+            ):
+                await asyncio.sleep(0.01)
+            assert process.returncode == 0
```

- **Do not apply:** moving `executor.shutdown(wait=True)` before `SHUTDOWN_ACK` and switching to bounded `process.communicate()` were both tested in disposable copies and still reproduced the failure; they are not acceptable fixes for this finding.
- **Minimum re-verification:** create a new append-only candidate containing only the test-oracle correction and any directly required documentation. On CPython 3.11, run the exact no-delay node 20 independent times, then all four affected files. Finally rerun a new complete candidate-gate portable matrix on CPython 3.11/3.12/3.13. Only a zero-Fail/Skip/XFail matrix may enter fresh Pi product/preflight/acceptance.
