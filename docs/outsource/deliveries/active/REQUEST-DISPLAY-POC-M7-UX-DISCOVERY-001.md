# REQUEST-DISPLAY-POC-M7-UX-DISCOVERY-001

- Date: 2026-09-16
- From: Core Designer; owner: Display POC team
- Status: `OPEN — AUTONOMOUS DISCOVERY AND DELIVERY`
- Work: M7 Display UX discovery; non-blocking input to later M7 Design
- Core baseline: `80d79d6c74ff93a40a018a03529c275287f2693e`
- Reserved return ID: `DELIVERY-DISPLAY-POC-M7-UX-DISCOVERY-001`
- Next exit: return one coherent delivery that makes the Display discovery input ready for later M7 Design
- Authority: USER authorized Core to issue this delivery. It does not authorize a Core agent to write another
  repository, operate target hardware or commit/push for the POC team; those actions follow the owning team's
  authority and workflow.

## 1. Outcome

Produce enough Raspberry Pi + physical OLED evidence for Core to choose an implementable, testable and durable
Display UX profile in later M7 Design without a second technology-discovery POC. This delivery prepares the
Display discovery input; it does not bypass M7's other milestone dependencies, including M6 acceptance.

The delivery must let Core answer:

1. Which screens, transitions and animations materially improve the product, and which should be excluded?
2. Which rendering and asset strategy should production use?
3. What frame-time, CPU, memory, asset-size and SPI-update envelope is realistic under representative product
   load?
4. What cancellation, timeout, failure fallback and OLED-protection policy should M7 adopt?
5. Which acceptance criteria are automatic, and which require human judgment on the physical OLED?

Playing an animation is not by itself success. Success means Core can convert the returned evidence into the M7
product selection, implementation design, resource budget and Test Spec.

## 2. Core baseline: preserve, map and challenge with evidence

The POC starts from the current Core boundaries. It may identify and recommend a change, but it must not silently
discard or replace them:

- Target profile is `DSP-PROFILE-OLED-128`: 128×128 RGB OLED, SSD1351, 1:1 logical canvas and current
  orientation/profile rules.
- Main-process startup and reverse shutdown remain owned by Resource Manager. Display must not create new State
  Manager states or change EventBus, worker, session, action or exit semantics.
- Product display flow remains `DisplayHint → RenderModel → Renderer → DisplayArbiter → DisplayDevice`, with
  Presenter, StatusBar and bounded fullscreen clients as the application roles.
- Arbiter calls remain synchronous on the event-loop thread; fullscreen uses a stable owner, has no queue or
  preemption, retains Normal backing state and releases in `finally`; physical presentation remains atomic.
- Display failure remains non-blocking to the conversation and must not change session state or process exit code.
- M4C owns basic State/Main/Error/Blank and whole-product wiring. Full icons, animation, state transitions and
  OLED protection remain M7 work. M4C does not wait for this POC.
- Current exclusions remain exclusions unless Core later adopts an evidence-backed delta: Progress UI, OSD,
  touch, LED, cross-owner fullscreen preemption, raw model output and full conversation history.

Normative sources are `docs/arch.md` §§2.3/5.3/6, `docs/display_spec.md`,
`docs/implement/ch02a_core_hal.md`, `docs/implement/ch08_display_arbiter.md`,
`docs/implement/ch10_config.md`, `docs/milestones/M4C.md` and `docs/milestones/M7.md` at the baseline above.

A recommendation that fits the baseline must map its runtime path and ownership to those contracts. If evidence
shows the baseline prevents every reasonable product direction, return a focused finding with the affected
contract, observed limitation, minimal proposed delta, regression surface and the cost of retaining the baseline.
Until Core adopts that finding, it is feedback rather than new authority. The final delivery must still identify
the best baseline-compatible direction, or explicitly prove why none exists.

## 3. Confirmed Core product requirements

Autonomy over method does not make the current product requirements optional. The POC may recommend static,
animated or deliberately restrained treatment, but its proposed UX must account for every applicable requirement
below rather than designing an unrelated demo.

### 3.1 Selected profile and visual foundation

- Preserve the 128×128 1:1 canvas, 20 px StatusBar, remaining Main region and mutually exclusive Fullscreen
  layout of `DSP-PROFILE-OLED-128`.
- Preserve the black background, current high-contrast foreground/error roles, safe rectangles and offline Noto
  Sans TC font baseline. Unsupported glyph, pixel-width wrapping, deterministic truncation and ellipsis behavior
  remain required for textual content.
- Keep Traditional Chinese as the primary product language while supporting the existing ASCII, number and basic
  punctuation baseline.

### 3.2 Required observable content

- Status must represent the authoritative states `IDLE`, `WAKE`, `PERCEPTION`, `THINK`, `ACTION` and `ERROR`
  using the existing product meaning; visual treatment must not invent additional State Manager states.
- Main must support the current turn's validated Perception text, the safe Tool action name, the actual Speak
  content, accepted interrupt feedback and sanitized error category/summary. It is a current-value surface, not a
  conversation-history or debug surface.
- Boot and graceful shutdown retain `fullscreen.blank` as the reliable fallback. M7 may add bounded boot and
  shutdown animation, but asset absence, failure, timeout or cancellation must still converge to the defined Blank
  behavior without delaying readiness, cleanup or shutdown.
- M7 planning already includes visual treatment for current content, volume, connection, capability and sanitized
  error, plus boot/shutdown and state-transition animation. Volume may be prototyped as a visual surface, but the
  current Core product only has startup-static volume; the POC must not assume a runtime volume-button feature has
  already been adopted.
- Long-lived OLED protection is an M7 decision input. The recommendation must address IDLE behavior and burn-in
  risk even if it concludes that no visible animation is appropriate.

### 3.3 Content, privacy and degradation behavior

- `show_session_content=false` must suppress Perception/Tool/Speak content without changing State, Error, Blank,
  session, audio, lifecycle or exit behavior.
- Credential, secret, prompt, hidden context, raw tool arguments, raw model output, exception detail, stack trace,
  stale session/turn content and full conversation history remain prohibited display content.
- Empty or fully sanitized content clears Main; stale content must not replace or clear the current valid screen.
- NullDisplay, missing glyph, unknown hint, renderer/HAL failure and unavailable assets must preserve the current
  fallback and non-blocking behavior.
- Progress UI, OSD, touch, LED and cross-owner fullscreen preemption remain outside the selected product unless
  returned as a focused finding and later adopted by Core.

The final return must include one concise **Core existing-requirements mapping** from `DSP-REQ-001` through
`DSP-REQ-009`, the `display_spec.md` scenario matrix and `M7.md` §9.1 to the recommendation. This is not nine
separate experiments, a replay of Accepted M3/M4C evidence or a new gate. Mark unaffected requirements as retained
inputs and state how the proposed UX preserves them; attach new evidence only where the POC recommendation depends
on or changes the behavior. Any unsupported, changed or still-inconclusive requirement must be explicit. A
visually compelling candidate that omits this mapping is not a complete delivery.

## 4. Delegated autonomy

The POC team owns the discovery plan. Core does not prescribe a command-by-command experiment sequence.

The team may independently choose and revise:

- prototype language, libraries, asset tools and repository organization;
- procedural drawing, frame sequences, sprites or other rendering candidates;
- visual directions, duration, frame pacing and prioritised scenarios;
- experiment order, repetition, failure diagnosis and candidate elimination;
- whether evidence supports rich animation, restrained transitions, static presentation or no animation;
- the smallest set of experiments that resolves the decision questions.

POC code may be disposable and may temporarily bypass a Core layer for isolated discovery. Such results are not
integration proof: the final recommendation must map back to the Core flow, or carry the focused contract finding
defined above. There is no requirement to reuse prototype code in Core.

Routine failures, tuning, reruns, tool selection and internal sequencing do not need Core approval or per-step
ACK. Return to Core before continuing only when the work requires one of these decisions:

- changing a Core architecture or public product contract;
- adding or replacing target hardware, an external runtime service or a user-visible product capability;
- choosing between materially different product directions that evidence alone cannot resolve;
- obtaining new cross-repository authority, protected/private input or a destructive/irreversible operation;
- resolving a blocker that leaves no meaningful baseline-compatible experiment.

## 5. Evidence obligations, not a prescribed test script

Choose experiments from the outcome questions rather than treating this section as a fixed case list. The final
evidence nevertheless must cover the following facts wherever the recommendation depends on them:

- the target Raspberry Pi and physical 128×128 SSD1351 OLED identity;
- physical frame presentation, update latency, pacing, flicker/tearing observations and failure behavior;
- CPU, memory, frame time, SPI flush and asset/storage cost under a representative LLM/TTS/Audio concurrent load;
- boot, shutdown and selected transition cancellation, timeout, ownership release and cleanup;
- long-lived IDLE/OLED protection implications, including what was measured versus only recommended;
- visual readability and product-value judgment on the physical panel;
- runtime-offline reproducibility and exact versions, locators, digests and licenses for retained dependencies and
  candidate assets.

The POC may explore more or less animation than currently planned. It must not expose credentials, private
conversation content, prompts, hidden context, raw model output or local host paths. Target runs must be bounded,
must not damage the OLED, and must leave hardware and processes in a recoverable state. Workstation asset creation
may use external tooling, but every recommended product runtime path must be offline and reproducible.

Human OLED observations are legitimate evidence for readability, flicker, perceived smoothness and product fit.
They complement rather than replace automatic timing, ownership, cancellation and cleanup evidence.

## 6. Return package

Return one coherent delivery under reserved ID `DELIVERY-DISPLAY-POC-M7-UX-DISCOVERY-001`. Internal experiment
files may use any useful structure; the Core-facing delivery must contain:

1. exact source commit SHA, dirty-state disposition, target identity, dependency/tool versions and repeatable
   commands;
2. one recommended product direction, rejected/secondary directions and evidence-based tradeoffs;
3. a decision table answering every §1 question as `SUPPORTED`, `REJECTED` or `INCONCLUSIVE` with locators;
4. the §3 Core existing-requirements mapping plus mapping of the recommendation to current Core ownership, hints,
   renderer, arbiter, lifecycle and failure paths;
5. public sanitized raw/derived metrics with method, sample scope and limitations—no unsupported percentile or
   product-threshold claims;
6. physical-panel visual evidence and the associated human observations;
7. candidate asset/dependency manifest with size, SHA-256, source, license and product-retention recommendation;
8. proposed automatic and human M7 acceptance criteria, clearly separated from measurements;
9. all architecture/product feedback as focused findings with minimal delta and regression impact;
10. remaining unknowns, explicit non-claims and whether the Display discovery input is sufficient for later M7
    Design once its other milestone dependencies are satisfied.

Large videos, frame captures and private raw logs stay outside Core Git. The delivery gives neutral locators and
digests; small sanitized tables and manifests may be returned in Git.

## 7. Exit and decision ownership

The POC team owns truthful execution and interpretation of its experiments. It does not approve Core architecture,
modify Core production code, release M7 gates or declare the product accepted. `DELIVERED` means the package is
complete enough for Core review, not that Core adopted the recommendation.

Core Designer reviews the return against this request, resolves any focused contract findings with the actual
authority owner, and then records what enters M7 product authority. An inconclusive direction may be returned
honestly with the evidence and remaining decision; do not tune, omit failures or expand indefinitely to force a
preferred answer.
