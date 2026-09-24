# Current development status

## Active M4C implementation — 2026-09-24

### Authority and execution model

- Developer entry is Open by `docs/status/current.md`. Product authority is
  `docs/milestones/M4C.md`; executable authority is `docs/test_spec/test_spec_M4C.md`, with later
  explicit USER decisions taking precedence where those owner documents are still stale.
- M4C uses two lanes. Discussion closes one scenario's stimuli, evidence, assertions and workstation
  try-run. Implementation then completes that scenario through workstation try-run and applicable Pi
  product testing. After every scenario converges, the final pending bytes receive one complete Pi PV
  before the M4C completion commit.
- Assertions must detect a stated product risk. Scenario startup and execution do not perform routine
  source, model, artifact, evidence or text digest work, generic close-proof, or owner enumeration.
  Content checks remain operator-triggered transfer/candidate diagnostics only when actually needed.
- Pi scenarios use the selected INMP441/ALSA input and I2S speaker. No M4C result depends on
  external capture or exact ASR wording.

### Current implementation result

- WP1–WP5 are implemented across fixed output volume, B2 streaming extraction/control, authenticated
  `SAFE_TEXT` delivery, streaming Speak and Display integration, no-input session policy, and the M4C
  scenario runner. The current affected production and regression changes are the pending working-tree
  files; no completion commit exists yet.
- Workstation verification is green: the complete non-RPi suite, focused M4C/M4B regressions,
  compilation and diff checks pass. Pi verification is green for the complete non-RPi suite and the
  focused startup/worker/runner/S02 matrices. A display-null cold start reached Resource Manager READY
  in 3.555 seconds with zero cleanup failures; ASR took 0.371 s, Matcha TTS 2.567 s and LiteRT-LM
  0.525 s. The OLED was not opened.
- Product startup/rebuild now uses bounded path-shape checks instead of repeatedly hashing the 2.58 GB
  model and runtime closure. Full digest helpers remain available only for explicit staging or
  candidate diagnostics. This removed the observed 60–90 second startup delay without changing native
  READY identity or offline/network-denial behavior.
- LiteRT-LM streaming now waits for asynchronous 0.16 callbacks after the native entry returns, and
  partial JSON immediately after `{"text":` is treated as incomplete rather than invalid. Timing
  validation checks generation and playback causal branches independently, allowing the required
  `audio_first_write < llm_terminal` overlap.

### S02 — implementation closed

- `M4C-PI-S02/NORMAL_END_B2` incorporates the former live-eligible S09 proof. Turn 1 requires
  `first_safe_text <= tts_first_pcm <= audio_first_write < llm_terminal`, complete ordered playback and
  drain, and equality between synthesized, terminal and final Display text. Turn 2 accepts the legal
  `speak, speak, rest` or `speak, rest` action branch and returns to IDLE. ASR text itself is not graded.
- Pi run `M4C-S02-DEV-20260924-09/A1` completed both physical-button/INMP441 turns, two streamed speaker
  answers, post-answer Rest, clean shutdown and return to IDLE. All product assertions preceding Display
  adjudication passed. Its immutable result card remains Fail only because the driver omitted the valid
  `("WAKE", null)` Main-clear publication from a duplicated expected ledger; this is a harness false
  negative, not a product failure.
- The Display expectation now comes from one oracle for both legal second-turn branches. The corrected
  workstation and Pi focused matrices pass, including checkpoint-before-adjudication coverage. Per USER
  direction, no duplicate physical interaction is required; the corrected harness runs again as part of
  final full M4C Pi PV. The initialized RUN10 was not executed and carries no result.

### Next work package — S03

- `M4C-PI-S03/TWO_TIMEOUTS` is discussion-closed and next in the implementation lane. One short press
  creates a Session/Conversation; two real 10-second INMP441 captures while the operator remains silent
  must each classify as `timeout`. The first plays exactly one fixed retry prompt to completion before
  the second capture. The second calls no LLM, plays no retry, executes Rest/END_SESSION and returns to
  IDLE with Status `待命` and empty Main.
- Public evidence retains the timeout/streak/action/count/order facts. Private evidence retains identities,
  correlations and native ASR/TTS/ALSA diagnostics. Exact ASR text is not asserted. Affected paths are the
  no-input portable tests, M4C Pi scenario driver and runner tests;
  estimate: 3 points.
- Next action: implement the S03 real-State-Manager/fake-native workstation path and fail-closed cases,
  run focused and affected regressions, then execute its single Pi product sub-run. Final full M4C PV
  remains pending until all scenarios are complete.

### Current authority route

- `docs/milestones/M4C.md` and `docs/test_spec/test_spec_M4C.md` now define the automatic
  `S02/NORMAL_END_B2`, the four-variant S09 catalog and the 16-run final PV. Update the runner
  to that catalog before final M4C PV; Developer owns the implementation change.
