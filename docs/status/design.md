# Current design status

- Owner: Designer
- Scope: M4C complete offline voice-device integration
- State: **M4C Accepted；formal Pi PV 7/7 Pass**
- Developer entry: **Closed**

## Accepted inputs

- M4A Audio supplies the production ASR／TTS／Audio lifecycle, existing public ports and exact artifact baseline.
- M4B LLM／Reasoner supplies the constrained terminal semantic contract, `snowboard.llm/3`, safe incremental S2
  source, Conversation lifecycle, resource observations and monotonic timing nodes.
- M4-ERR is Accepted at commit `f572915d0b0d5c52067e9100c5b022e57aefe506` after same-bytes Raspberry Pi
  run `M4-ERR-DEV-04`; M4C consumes its typed faults, backend disposition, recovery and fatal-exit behavior.
- Accepted-history evidence remains immutable. M4C is a prospective composition delta and must reverify only
  directly affected inheritance plus its whole-product scenarios on the final bytes.

## M4C-SS disposition

- Designer adopts `B2-ONE-LOOKAHEAD-COALESCE` as the only real-model streaming-speak product path and fixes
  the M4C S2 boundary at punctuation or 12 normalized codepoints.
- The source delivery is bound to POC commits `a6de0e66d7effe03549037eb8f50b99e42399620` and
  `a492a1416721c73c989dd46067b3e9dd1c24508d`; the preserved Core file SHA-256 is
  `c097d550d263070ef216bfa391e87c69b6b27aa68baf26f09ea7428be8bf069f`.
- The POC proved a usable pre-terminal raw-stream path, existing-interface B2 mapping and bounded cleanup in
  engineering runs. It does not provide formal Core acceptance:
  0/82 formal cases ran, the Pi checkout was dirty, the live A result was projected, and the full negative,
  resource and human-quality matrices were omitted.
- Those limitations are routed into M4C Test Spec and final same-bytes Pi Verify. No POC row may be credited as
  a product PASS, and no second A-mode acceptance path or runtime A/B switch may be introduced.

## Fixed product design

The authoritative behavior is [`M4C`](../milestones/M4C.md). It fixes:

- one SM-owned private streaming control per generated speak turn, with terminal `LLMResponse` and one
  `ActionCompleted(ok)` remaining the only public cognition／action Facts;
- a two-fragment／256-byte backpressured queue, B2 exact one-available-lookahead concatenation, sequential
  existing-TTS calls and no public Audio／TTS API change;
- terminal-only degeneration inside B2 when no pre-terminal fragment exists; once any fragment is admitted,
  full-terminal replay and fallback-to-A are forbidden;
- shared cancellation of generation／queue／TTS／Audio, M4-ERR error mapping, rejection of stale／late output,
  and zero-owner cleanup before reuse or recovery;
- startup-static output volume 25%, complete no-input Session behavior, no barge-in, five Pi product
  scenarios／seven sub-runs, and focused workstation closure for streaming faults and Display degradation.

## Streamlined verification disposition

- S01–S05 remain the complete Pi product catalog: START_IDLE, NORMAL_END_B2, TWO_TIMEOUTS,
  PERCEPTION／THINK／ACTION interrupt and APP_EXIT.
- S06 retains only two portable integration risks: partial streaming followed by LLM backend fault, and a
  TTS child fault while StreamingSpeak owns queued/inflight work. Accepted M4-ERR remains authority for the
  ASR／LLM／TTS fault matrix, rebuild and ERROR recovery.
- S07 retains one workstation vertical proving that a THINK-time Display failure disables rendering without
  interrupting the voice path. S08 adds no test because existing M4B／M4-ERR coverage proves the complete
  READY-rejection-to-exit-4 chain.
- S09 has no independent scenario: S02 owns normal audible B2 behavior, C14/C15 own queued/synthesizing
  cancellation, and S04/ACTION owns real playback interruption.
- SHA/digest, authorization, generic closure, global owner enumeration and repeated fresh-run bookkeeping
  are not M4C product assertions. Only lifecycle observations directly required by interrupt, recovery or
  shutdown remain.

## Acceptance disposition

Candidate `0b2160e5d48dcc959b08f4a23ede91a9e0d5640d` completed formal Pi run
`M4C-FORMAL-PV-20260926-01`: all seven catalog entries are designated Pass and the finalizer reports
`pv_status=Pass`. The fixed Pi checkout remained clean and matched the workstation tracked-content SHA-256
`d5d94f7c539c3f8de276f3974876074ac43bae810bb1cdab08bf9b9bd93a3502` after execution. M4C is closed;
future work does not reopen it unless a concrete regression is found.
