# M4C — complete offline voice device integration

Date: 2026-09-06. Status: Designer planning complete; affected contract review and entry selections pending, not Development Ready.

## Deliverable

Button -> Listen/ASR -> Reasoner/LLM -> Speak/TTS -> Listen or IDLE, with basic Session Display, interruption, session reset and repeatable App lifecycle. M4C completes these functions; ALPHA does not fill missing basic wiring. Camera/look and voice wake stay M6; tool/MQTT stay M5; polished graphics/animation stay M7.

M4A and M4B are accepted inputs. Use M4B selected model encoding and incremental seam. Full-response mode is retained for comparison; implement one streaming speak operation that consumes validated body text at punctuation or 24-codepoint boundaries. Queue bound proposal: two chunks, pause producer at capacity; if upstream cannot pause safely, cancel on bounded backpressure timeout. No unbounded buffering or dropped text. End marker releases no speech. Invalid terminal/interrupt/reset cancels production and drains/discards pending TTS, waits for playback ownership release, then ends session. Already played speech remains an explicit failure limitation. Final exact queue/timeout contract requires affected architecture review and selected runtime proof.

## User operation and Display

- Start: provision an explicit external launcher entry; App initialization is bounded and failures observable. Default proposal is manual launcher start, no automatic boot or new button gesture without User product selection. Auto-start versus button launch is an entry decision, not silently assumed authorization for system services.
- Ready: admit conversation only after required resources ready. Display planning adds basic preparing/ready/error indication; reconcile with current boot-Blank specification before implementation. No animation/icons required.
- Short press: use existing state-dependent ButtonPressed behavior for wake/interrupt; verify complete cancel then fresh wake, no hidden old context. Long press retains App shutdown, not reset/reboot.
- Reset: end current conversation through interrupt convergence, return IDLE; fresh wake starts empty. No factory reset, configuration erasure or Pi power control.
- Shutdown: cancel all work, blank/release Display and hardware, exit; launcher can start a fresh App with released resources. External launcher starts an exited App; App does not implement its own supervisor.

## Work packages and entry

1. Selected M4B seam -> Reasoner/SM/TTS integration; affected architecture approval precedes code.
2. Lifecycle/launcher/control and basic Display specification reconciliation; User resolves start-mode choice before implementing launcher binding.
3. Accepted Audio+LLM combined resource measurement: choose MemAvailable reserve/hysteresis from observed worst supported workload, validate pressure/fault/one-recovery behavior. POC subsystem headroom is not product capacity evidence.
4. Complete-flow target acceptance and final M4 delivery. Tester maps existing shared-path tests, avoiding repeated unchanged M4A-only qualification.

## Completion evidence

At one final candidate: normal two-turn voice session, explicit end, idle reset, interrupt during each active stage, context-full end, restart after App shutdown, startup failure and recoverable/fatal runtime failures. Display follows actual lifecycle and clears old-session content; no stale audio/results, no orphan resource owners. Validate injected faults automatically and exercise relevant physical paths on Pi.

Freeze public fixture/audio duration, speech-end annotation, run count, deployment/profile and measurement error before target execution. Record ASR completion, LLM first usable chunk, first TTS submission and physical meaningful audible onset on one clock, including first and subsequent turns. Null onset without proof cannot complete this integrated measurement requirement. New Audio target execution still needs User/operator authorization.

Record response/recovery performance against ALPHA targets without declaring target compliance on misses; implement selected latency remedies and name remaining measurable gaps. Combined soak proposal: 20 complete two-turn sessions plus separate controlled recovery, no session-count recycle. No OOM/swap growth/thermal violation or failed cleanup; retain all samples. M4C closure requires functionality and safe combined operation, not arbitrary subjective answer preference.

M4 Accepted reconciles M4A/B/C on the final delivery SHA through unchanged evidence inheritance plus affected-path verification, not blind re-execution of all historic POC. Exact candidate workflow remains authoritative.
