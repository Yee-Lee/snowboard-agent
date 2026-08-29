# GATE2B-PI-PACKET-001 — Cumulative Audio + LLM Final Validation

- **Packet ID**: `G2B-PI-COMBINED-001`
- **Revision**: `2026-08-29-r6-audio-runtime-closure-inputs`
- **Status**: `USER AUTHORIZED COMMIT/PUSH + PI EXECUTION / RESULT REVIEW REQUIRED`
- **Entry receipts**: User-reviewed Gemma model-finalist receipt and Core-accepted Audio handoff
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

The User reviewed the final Gate 2A evidence and selected Gemma as the sole model finalist. Qwen is
excluded from formal Gate 2B. Gemma's immutable P2/P8 FAIL observations remain in the entry receipt;
they are not relabelled as PASS. The old product pairing is rejected, and Gate 2B binds a new generic
structured-product prompt revision. Its first model contact is this held-out 20-session combined run;
no scored Audio transcript or expected response is used to tune the prompt beforehand. Core ACK of
the Gate 2A semantic split may arrive during execution but is mandatory before final Gate 2 delivery.

## 2. Single combined execution

P9 and P10B share one 4GB `swap=0` offline execution so Audio and LLM models are not loaded twice.
The POC combined controller imports the exact clean Core HAL checkout and starts the accepted
VAD/ASR/TTS components plus the User-reviewed model-finalist LLM child. This is the contracted POC
boundary; it does not claim that the Core product composition root is under test. It then performs:

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
protocol pipe, or a post-READY VAD/ASR/TTS session failure, and other observed
candidate/resource/cleanup violations are `FAIL`. Installer, LLM stderr and accepted ASR stderr are
all scanned against static and runtime-sensitive markers before disposable work is removed.

## 4. Final cumulative decision

The final manifest links:

- Gate 1: P1/P6/P7/P10A/P11/P12;
- Gate 2A: immutable P2/P3/P4/P5/P8 observations plus the User model-finalist decision; and
- Gate 2B: P9/P10B.

Gate 2B does not overwrite the old P2/P8 machine results. P10B independently decides whether the new
Gemma voice integration completes all 20 held-out Audio sessions with schema-valid current-session
speech and no history contamination. Only after P9/P10B PASS and User evidence review may the POC
submit a final winner proposal. Core must explicitly ACK the semantic split and residual non-voice
product-qualification boundary before final acceptance.

## 5. Reviewer and execution gate

The executable candidate binds the Accepted Audio entry schema, immutable Gemma model-finalist
receipt, Gate 2B structured-prompt adapter/config, runner, artifact-independent coordinator,
sampler/calculations, result schema and all repository checksums in `gate2b-pi-lock-v1.json`.
External Audio and Core checkouts
must be clean and exact. Before residency timing, the runner verifies the exact 20-WAV fixture lock
and delivered fixture manifest, VAD model, ASR worker/model, TTS archive/vocoder and both isolated
Audio runtime identities. These one-time static checks are outside LLM READY and P9/P10B timing. The
entry verifier hashes and schema-validates the actual User-reviewed Gate 2A result named by its
receipt; a receipt without its bound result cannot authorize Gate 2B. On 2026-08-29 the User
explicitly authorized this completed replacement to be committed/pushed and executed on Pi without
waiting for Core result ACK or independent review; parallel review may follow and cannot rewrite the
frozen attempt. The Gate 2A receipt itself is repo-locked; the
external sanitized result named by it must match byte-for-byte.

`run_gate2b_pi_v1.py` requires the exact LLM execution SHA, accepted Audio/Core roots, controlled
Audio fixture/artifact/runtime paths, one Gate 2A receipt and its unchanged model receipt. The Audio
pre-residency boundary includes both sherpa-onnx wheel source identities required by the Accepted TTS
domain, even though execution uses the already-authenticated isolated runtime. It hashes no model
during READY or combined timing. The formal replacement command shape is:

As in the accepted Gate 2A packet, the offline launch must use a private mount namespace and mount
read-only sysfs after entering the private network namespace. A network namespace alone clears the
routes but can inherit the host sysfs view and falsely observe host `wlan0=up`; host Wi-Fi must not
be disabled to satisfy this check.

Initial formal attempt `G2B-PI-COMBINED-001` at execution SHA `2dd7d28270afe15d2b31ab8c4ee5c3c98b694cd5`
is retained as `INCONCLUSIVE`: the controlled store omitted the two TTS wheel source files required
by the Accepted Audio startup verifier. VAD and ASR started, TTS rejected the incomplete store, LLM
did not start, zero sessions ran, and cleanup returned zero residue. Its sanitized evidence SHA-256
is `50714d383cbefb75b96ae320e86bbb1ca64756f897f6b05eddd64f4f61a008f0`. The replacement uses a new
run ID/evidence root and verifies both wheel identities before any domain becomes resident.

```sh
unshare --user --map-root-user --mount --net -- env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin OPENBLAS_NUM_THREADS=1 PYTHONNOUSERSITE=1 sh -ec 'mount -t sysfs -o ro sysfs /sys; exec python3 poc_llm/tools/run_gate2b_pi_v1.py --packet-lock poc_llm/harness/gate2b-pi-lock-v1.json --gate2a-receipt poc_llm/fixtures/gate2/gate2a-gemma-model-finalist-001.json --gate2a-result <user-reviewed-gate2a-sanitized.json> --artifact-receipt <unchanged-model-receipt.json> --accepted-audio-entry poc_llm/fixtures/gate2/accepted-audio-entry-001.json --execution-sha <clean-execution-sha> --run-id G2B-PI-COMBINED-002 --evidence-root <new-controlled-evidence-root> --audio-root <clean-audio-completion-root> --core-root <clean-core-hal-root> --audio-fixture-dir <accepted-fixture-dir> --audio-fixture-lock <accepted-fixture-lock.json> --audio-fixture-manifest <accepted-delivered-fixture-manifest.json> --audio-artifact-dir <accepted-audio-artifact-dir> --audio-runtime-python <accepted-tts-python> --audio-asr-binary <accepted-whisper-worker> --audio-asr-model <accepted-base-q8-model> --audio-vad-runtime-python <accepted-vad-python> --audio-vad-model <accepted-silero-model> --input-device hw:0,0 --output-device hw:0,0 --input-channel 0'
```

Raw resource samples and disposable Audio work data stay outside Git. Sanitized evidence contains
only hashes, terminals, timings, process/resource counters and cleanup disposition. Hardware output
remains review-required and cannot be committed or delivered as PASS before User review.
