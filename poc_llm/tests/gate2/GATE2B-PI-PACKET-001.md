# GATE2B-PI-PACKET-001 — Cumulative Audio + LLM Final Validation

- **Packet ID**: `G2B-PI-COMBINED-001`
- **Revision**: `2026-08-28-r3-fail-closed-evidence`
- **Status**: `EXECUTABLE CANDIDATE / REVIEWER CHECK REQUIRED / NOT AUTHORIZED`
- **Entry receipts**: User-reviewed Gate 2A provisional receipt and Core-accepted Audio handoff
- **Formal credit executed here**: M4B-P9, P10B
- **Outcome ceiling**: final POC winner recommendation; Core decides

## 1. No broad regression rule

Gate 2B does not automatically rerun P1～P8/P10A/P11/P12. It authenticates their manifest chain and
the exact candidate/runtime/model/config/protocol/fixture/source identities. Only a component or
boundary changed by combined integration triggers a focused, predeclared affected-item regression.
Unchanged accepted evidence remains valid.

The surrogate P9 envelope is planning/debug input only. Formal P9/P10B uses Accepted Audio delivery
`POC-audio-DEL-2026-001-R1`, annotated tag `audio_m4` (tag-object SHA
`24b2571a23dde2f77027242b61142b0c1a59924c`) targeting accepted completion SHA
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`, corrected delivery SHA
`ca51bce9b4e205d9c9faf004d41c27169f108a3f`, Core response
`RESP-AUDIO-M4-GATE2B-001` at `be19b70b1dd91674e7ff981eb9d6b2dca9741f54`, and Core HAL
checkout `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf`.

The User-authorized accelerated sequence permits Gate 2B execution after the Gate 2A evidence is
User-reviewed; the Gate 2A Core ACK may arrive during execution but is mandatory before final Gate 2
delivery. This does not relax Qwen: selecting Qwen requires its written workaround disposition to be
accepted by both User and Core before Gate 2B entry.

## 2. Single combined execution

P9 and P10B share one 4GB `swap=0` offline execution so Audio and LLM models are not loaded twice.
The controller starts the real Core parent boundary, accepted VAD/ASR/TTS components and the
User-reviewed provisional LLM child, then performs:

1. authenticated idle and simultaneous-residency samples before the first session;
2. twenty frozen VAD→ASR→LLM→TTS sessions using the 128-input/64-output LLM product profile at
   five-second cadence; the ASR transcript exists only
   in memory, feeds the real LLM, and the LLM `speak` text exists only in memory before feeding the
   accepted TTS;
3. per-session end-to-end and LLM timings, schema disposition, `MemTotal-MemAvailable`, full process-
   tree PSS/RSS, CPU, threads/process ownership, temperature, throttling and PSI;
4. the predeclared combined fault schedule, which is empty because the integration adds no new
   cancel/failure protocol and both accepted child boundaries retain their reviewed failure credit;
   this does not replay or claim new failure credit; and
5. reverse-order shutdown, waitpid and zero owner/process residue followed by the offline proof.

## 3. P9 and P10B decisions

P9 `PASS` requires every 4GB sample to keep system-used memory <=3584 MiB, `swap=0`, no OOM, no
increase in full memory-pressure stall, complete process ownership and valid cleanup. Sum RSS is
diagnostic only. One stable resource point is captured after every session. Sessions 6–20 combined
PSS and system-used slopes must each be <=4.0 MiB/session, and sessions 16–20 medians must be no more
than 64 MiB above sessions 1–5; per-owner PSS leak diagnostics are also retained. An optional 8GB run
uses the identical configuration and cannot repair 4GB failure.

P10B `PASS` requires 20/20 combined sessions, 19 measured pauses of at least five seconds, accepted
Audio semantics, correlated valid LLM `speak` results containing the current session marker exactly
once (and no current trap/prior marker), whose text is actually consumed by TTS,
temperature <80°C, `throttled=0x0`, no crash/leak/stale result/history contamination and final zero
residue. No sample is removed and no post-result threshold change is allowed.

Every domain is registered for cleanup before `start()` is awaited. Its root is captured immediately
after successful start, or recovered from residency identity when start raises after allocation.
Cooperative reverse stop is followed by bounded
owner-specific TERM/KILL and absence checks when needed; any stop error or fallback is non-PASS even
when residue is removed. Partial-start cleanup proof is retained even if full residency and sampling
were never reached. The independent result verifier recomputes P9/P10B from sessions, continuous
and per-session resource samples, log-scan disposition and cleanup proofs. Infrastructure/probe/I/O
failures remain `INCONCLUSIVE`; a scored post-READY LLM deadline, EOF, invalid frame or broken/reset
protocol pipe and other observed candidate/resource/cleanup violations are `FAIL`.

## 4. Final cumulative decision

The final manifest links:

- Gate 1: P1/P6/P7/P10A/P11/P12;
- Gate 2A: P2/P3/P4/P5/P8; and
- Gate 2B: P9/P10B.

Only after all mandatory items and any P4 written disposition are accepted may the User approve a
winner proposal for Core. The POC state remains `Ready for internal review` until Core issues the
final winner ACK.

## 5. Reviewer and execution gate

The executable candidate binds the Accepted Audio entry schema, Gate 2A provisional receipt schema,
runner, artifact-independent coordinator, sampler/calculations, result schema, two frozen LLM
configs and all repository checksums in `gate2b-pi-lock-v1.json`. External Audio and Core checkouts
must be clean and exact; Audio fixture/artifact locks retain their own controlled checksums. The
entry verifier hashes and schema-validates the actual User-reviewed Gate 2A result named by its
receipt; a receipt without its bound result cannot authorize Gate 2B. Reviewer
approval is required before commit/push or any combined Pi run.

`run_gate2b_pi_v1.py` requires the exact LLM execution SHA, accepted Audio/Core roots, controlled
Audio fixture/artifact/runtime paths, one Gate 2A receipt and its unchanged model receipt. It hashes
no model during READY or combined timing. The formal command shape is:

```sh
unshare --user --map-root-user --net -- env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin OPENBLAS_NUM_THREADS=1 PYTHONNOUSERSITE=1 python3 poc_llm/tools/run_gate2b_pi_v1.py --packet-lock poc_llm/harness/gate2b-pi-lock-v1.json --gate2a-receipt <gate2a-provisional-receipt.json> --gate2a-result <user-reviewed-gate2a-sanitized.json> --artifact-receipt <unchanged-model-receipt.json> --accepted-audio-entry poc_llm/fixtures/gate2/accepted-audio-entry-001.json --execution-sha <clean-execution-sha> --run-id G2B-PI-COMBINED-001 --evidence-root <controlled-evidence-root> --audio-root <clean-audio-completion-root> --core-root <clean-core-hal-root> --audio-fixture-dir <accepted-fixture-dir> --audio-fixture-lock <accepted-fixture-lock.json> --audio-artifact-dir <accepted-audio-artifact-dir> --audio-runtime-python <accepted-tts-python> --audio-asr-binary <accepted-whisper-worker> --audio-asr-model <accepted-base-q8-model> --audio-vad-runtime-python <accepted-vad-python> --audio-vad-model <accepted-silero-model> --input-device hw:0,0 --output-device hw:0,0 --input-channel 0
```

Raw resource samples and disposable Audio work data stay outside Git. Sanitized evidence contains
only hashes, terminals, timings, process/resource counters and cleanup disposition. Hardware output
remains review-required and cannot be committed or delivered as PASS before User review.
