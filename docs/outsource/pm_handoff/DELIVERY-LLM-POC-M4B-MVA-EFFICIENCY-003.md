# DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003 — engineering findings and Core revision request

- Date: 2026-09-08
- Status: `USER APPROVED / CORE REVIEW REQUESTED / ENGINEERING NON-FORMAL`
- Plan baseline: `c91fce9`
- Evidence class: Pi engineering observations only; no formal hardware result
- User publication approval: 2026-09-08
- Delivery commit: reported with the pushed handoff; intentionally not self-prefilled

## Executive findings

1. Keep constrained JSON (`J`) as the safe encoding. Prefix encoding (`P`) is supported by the
   frozen runtime but regressed explicit-end intent. Retain constrained-J incremental extraction
   (`S2`) as the only streaming proposal; do not pursue `S3` or `S4`.
2. `H` moves Conversation construction before the request and saves about 3.1 seconds on the first
   request. `D` and `H` reach approximately the same post-request memory level, so `H` changes when
   memory is allocated rather than the eventual request-path footprint. Recommend `H` when a
   predictive 30-second hold and roughly 253 MiB early allocation are acceptable.
3. The listen-only Reasoner reference is viable: it validates the product envelope, projects only
   normalized listen text into the model user role, applies bounded admission, and owns the final
   `speak/listen` versus `rest` action. Other perceptions remain extension points, not implemented
   capabilities.
4. Retain exact `V1` only as evidence that detailed instructions can improve outcomes, not as an
   eligible prompt: it contains legacy session
   and protocol responsibilities and has no personality setting. `V2A` and `V2B` failed the public
   functional screen. The User-authorized `V2C` repair fixed their output-contract failures and
   passed all mechanical checks, but failed repeated answer correctness and concise-output review.
   No prompt candidate is currently qualified, and the POC has not yet established the key design
   method for combining compactness, correctness, personality and response-length control.
5. Do not use fake-first-turn prewarm. There is no clean prefix-KV snapshot API, and earlier repeated
   same-Engine tests retained the full first-turn prefill with only a small general warm effect.

The User approved these engineering findings for Core review. They are a Core revision request, not
a formal benchmark or gate disposition.

## C1 — Encoding and readiness closure

### Encoding

| Item | Engineering observation | Draft disposition |
| --- | --- | --- |
| `J` | Exact constrained `text/end` baseline; incremental parser safely withholds invalid terminal output | retain |
| `P` | LiteRT-LM 0.16 regex path and parser are technically executable | feasibility confirmed |
| `P` end behavior | Model produced answer text instead of the required exact end form in the explicit-end path | reject as current candidate |
| `S2` | Constrained-J text can be released incrementally while terminal validation remains authoritative | send to Core as fallback proposal |
| `S3/S4` | Stopped by User scope convergence | no further work |

The original Core five-pair formal J/P matrix was not run after the surface changed. The result above
is engineering discovery and must not be represented as a formal A/B result.

### D/H readiness and memory

The retained H observation showed about 442.39 MiB PSS at Engine-ready and about 252.83 MiB additional
PSS when the clean Conversation was held, for roughly 695 MiB before the user request. The exact raw H
record was not retained on disk, so these H values are reported at the precision available from the
reviewed engineering session rather than reconstructed with invented digits.

The single missing matched D lifecycle observation was collected on the same Pi/runtime class:

| D lifecycle point | PSS MiB |
| --- | ---: |
| Engine ready | 448.325 |
| Direct Conversation open | 701.138 |
| After one V1/J request | 1743.169 |
| One second after Conversation close | 1722.638 |
| After Engine close | 577.778 |

D allocated 252.813 MiB at session open, matching the approximate H hold allocation. Only 20.531 MiB
was recovered one second after Conversation close; the large request-path allocation persisted until
Engine close. The earlier H run showed the same qualitative lifecycle and about 497.33 MiB after
Engine close. The between-run final-PSS difference is not interpreted from one observation per mode.

The D request had 147 rendered tokens, 148 runtime-prefill tokens, 4.067-second first safe chunk and
4.763-second terminal generation time. Session open separately took 3.126 seconds. H's principal gain
is moving approximately that open cost before the request; it is not a lower eventual memory mode.

## C2 — Minimum listen-only Reasoner result

The reference implementation now provides:

- an explicit `PerceptionProjector` seam with only `ListenProjector` implemented;
- exact envelope and frozen `SessionFacts` validation;
- typed empty/failed/multiple/unsupported-input failures;
- a 20-codepoint listen limit and temporary 32-token single-listen safety check;
- full rendered/KV/output-reserve admission against 1024 tokens;
- 128-token rendered/runtime performance classification without rejection;
- direct model-facing listen text, with product envelope fields excluded from model input;
- exact `SemanticGeneration(text,end)` validation and deterministic `speak/listen` or `rest`
  projection; and
- isolated instances with no cross-session state.

Workstation efficiency plus MVA regression: 113 passed. Pi dependency-free efficiency regression:
41 passed. A real Pi V1/J request used the new envelope-to-action path and returned `speak`. These are
implementation checks, not formal packet evidence.

For future multi-input work, the projector collection is the extension boundary. The 32-token check
must not be copied as the future aggregate limit; Core will need an aggregate rendered/KV policy when
additional input kinds are implemented.

## C3 — Prompt findings

### Prior controlled findings retained without repetition

| Prompt | System tokens | Result |
| --- | ---: | --- |
| `V1` | 113 | detailed legacy instruction oracle; not eligible for adoption |
| `V2.1` | 37 | 21/21 semantic failures; rejected |
| `V2.1P` | 46 | 18/21 semantic failures; rejected |
| `V2.2` | 56 | structure/end 36/36, but capability semantics failed |
| `V2.2P` | 65 | structure/end 36/36, capability failed; answer median grew from 25 to 41 codepoints |

`V2.2P` did not delay first streaming text materially; its worse terminal time came mainly from
generating more answer content. This confirms that personality must be evaluated for response-length
behavior, not merely prompt-token overhead.

### Direct-text Reasoner screen

The first JSON-enveloped V2A/V2B diagnostic was discarded from the final prompt comparison because it
revealed that an early implementation accidentally rewrapped the already-decoded listen input. The
Reasoner was corrected, its regression tests passed on workstation and Pi, and the same candidates
were rerun with direct text. No new candidate or case was added.

| Candidate | System composition | Runtime prefill on successful public cases | Public result |
| --- | --- | ---: | --- |
| `V2A` | 71 core + 9 personality = 80 | 99–102 | failed: identity/basic/tool invalid; see capability failed |
| `V2B` | 75 core + 9 personality = 84 | 103–106 | failed: identity/basic invalid; other four cases passed |
| `V2C` | 100 core + 9 personality = 109 | 126–131 first-turn cases | mechanical 12/12; correctness and brevity failed |
| exact `V1` | 113, no personality | 128–134 | screen 6/6; confirmation 6/6 |

Neither V2A nor V2B reached confirmation. After User review of their failure, the User explicitly
authorized one `V2C` repair that restores only the model-facing JSON and `end` semantics, retains the
separate nine-token personality setting, records public answers and exposes sanitized parser failure
subtypes. No further candidate was created.

V2A/V2B were deliberately brief explorations, not causal ablations. Their earlier runner retained
only the top-level `INVALID_OUTPUT` code, so the report does not attribute every failure to one exact
parser condition. They establish that those complete candidate texts were not usable; they do not
establish which individual deleted phrase caused the failures.

### User-authorized V2C result

V2C core text:

```text
你是「雪板」繁體中文語音助理，簡短、正確回答。你只能聆聽並說話；不能看見環境或使用工具。每次只輸出符合指定 schema 的 JSON，且只含 text 與 end。end 表示是否結束整個對話，不是本次回答是否完成。一般回答須為非空 text、end=false；只有使用者明確要求結束對話時，才輸出空 text、end=true。語氣不增加內容：
```

The trusted setting `溫暖自然，稍帶幽默。` adds nine tokens. Core, setting and complete system
counts are 100, 9 and 109 tokens respectively.

| Public case | User / rendered / runtime-prefill tokens | Answer | Mechanical result |
| --- | --- | --- | --- |
| Identity | 3 / 125 / 126 | `我是雪板的語音助理，很高興為您服務！` | PASS |
| Basic | 6 / 128 / 129 | `天空是藍色的，主要是因為光線在地球大氣中會發生散射，特別是瑞利散射。藍色光波長較短，更容易被氣體分子散射，所以我們看到的天空通常是藍色的。` | PASS |
| Cannot see | 5 / 127 / 128 | `我聽得見您，但看不到您呢。😊` | PASS |
| Cannot use tools | 5 / 127 / 128 | `我目前只能聆聽和說話，沒有使用工具的能力喔！` | PASS |
| Explicit end | 7 / 129 / 130 | empty text, `end=true` | PASS |
| Negative end | 8 / 130 / 131 | `好的，沒問題！我會說得更簡單一點，您想問什麼呢？` | PASS |

The independent public cases had a 1.910-second median first safe chunk for non-end answers and a
3.356-second median terminal time across all six cases. The longest basic answer used 62 output
tokens, 69 codepoints and 6.919 seconds to reach terminal despite the concise instruction.

The three confirmation pairs reproduced deterministically:

| Input | Repetitions | User / rendered / runtime-prefill tokens | Answer | Safe-chunk median | Terminal median |
| --- | ---: | --- | --- | ---: | ---: |
| `你好？` | 3 | 2 / 124 / 125 | `您好！我是雪板的語音助理，隨時為您服務呢。您有什麼需要我幫忙的嗎？` | 1.366 s | 4.418 s |
| `請用一句話說明天空為什麼看起來是藍色的？` | 3 | 13 / 21 / 21 | `明天看起來是藍色，可能是因為天空的氣流和光線在特定角度下，讓藍光更顯眼呢！` | 1.634 s | 4.415 s |

Although the runner's structural oracle reported confirmation 6/6, human semantic review overrides
that mechanical result. All three 20-codepoint answers misread `天空` as `明天` and gave an inaccurate
airflow/angle explanation, so basic correctness is 0/3 for that repeated answer. V2C also lengthened
every non-end public answer relative to V1: identity 18 versus 13 codepoints, basic 69 versus 46,
cannot-see 14 versus 8, cannot-tool 22 versus 8, and negative-end 24 versus 11. The personality is
visible in `呢`, `喔` and the emoji, but the instruction that style must not add content did not work.

V2C therefore proves the narrow hypothesis that explicit output-format and conversation-end semantics
can restore structural stability. It does not qualify the complete prompt because correctness and
conciseness remain required.

### Exact V1 legacy-oracle timing on direct-text input

All values below are engineering-only Pi observations. “Safe chunk” means the first punctuation,
24-codepoint chunk, or normally validated short terminal chunk available to a downstream TTS worker;
it is not audible onset.

| Case group | Runtime prefill | First decodable median | First safe chunk median | Terminal median |
| --- | ---: | ---: | ---: | ---: |
| Six independent public screen cases | 129–134 | 1.823 s (non-end) | 2.188 s (non-end) | 3.096 s |
| Three first-turn short questions | 128 | 1.192 s | 1.374 s | 4.011 s |
| Three second-turn 20-codepoint questions | 21 | 1.190 s | 1.554 s | 3.369 s |

The 20-codepoint question tokenized to 13 new-user tokens. It did not cause a large response-start
penalty. Its 21-token runtime prefill is the normal benefit of genuine same-session Conversation/KV
reuse, not fake prewarm. Earlier controlled 5/17/32-token question tests within one prefill signature
also showed no material latency separation.

V1 is not an adoption candidate despite these measurements. Its only prompt-design contribution is
showing that more detailed, imperative output/capability instructions produced better results than
the tested compact prompts.

The exact boundary test remains relevant: moving from runtime prefill 128 to 129 added about 0.63
seconds in that controlled pair. This is a performance tier transition, not a reason to reject input.
The V1 public screen still produced safe chunks within 2.28 seconds despite runtime prefill 129–134;
the basic-answer terminal extended to 5.73 seconds because output length was 49 tokens. Streaming is
therefore essential to the three-second audible-response objective, but Audio/TTS onset remains
unmeasured and no three-second E2E claim is made.

## Prompt-design knowledge and disposition

The round established four useful design facts:

1. Removing the product perception envelope saves tokens and belongs in Reasoner.
2. The model still needs explicit `text/end` semantics; constrained JSON shape alone is insufficient.
3. Explicit capability wording can make listen/speak, vision and tool answers mechanically correct.
4. A short personality suffix can visibly change style, but `語氣不增加內容` did not prevent longer
   answers and did not preserve repeated factual correctness.

It did not establish the critical final method:

- the minimum detailed instruction set that preserves V1-level behavior without its legacy policy;
- how to combine personality with concise answers;
- how to preserve basic correctness across the 20-codepoint voice range; or
- how much functional coverage is sufficient before a prompt can be frozen for Core.

The correct conclusion is therefore that the POC has not yet fully mastered the key prompt-design
method. More detailed output instructions are a promising and evidenced direction, but neither token
count nor mechanical `text/end` success predicts overall prompt quality.

There is no qualified final prompt proposal in this round. The evidence-supported disposition is:

- do not use V1; cite it only as evidence that detailed instructions can improve outcomes;
- send only Reasoner-projected user content in the model user role;
- keep JSON `text/end` constrained decoding and S2 incremental release;
- keep the 20-codepoint voice boundary and separate future 20-codepoint trusted-settings boundary;
- treat 128 as performance telemetry and 1024 as the hard context boundary; and
- carry the successful V2C output-semantics wording into any later prompt work, but do not select V2C
  until a candidate passes exact answer review and controls response length as well as structure.

V2C is fast enough to offer an LLM safe chunk before two seconds in the confirmation pairs, but speed
does not compensate for a deterministic wrong answer or materially longer responses. Personality
remains an important, demonstrated but unqualified feature.

## User-approved disposition and Core requests

The User approved publication, workstation commit/push, and delivery of this bounded result to Core
on 2026-09-08. Core is asked to review:

1. constrained JSON plus S2 incremental semantic extraction as the encoding direction;
2. conditional H readiness when the product can predict a 30-second interaction window and reserve
   about 253 MiB before the request;
3. the listen-only Reasoner boundary, including direct-text model input and future projector seams;
4. the revised formal packet scope and controls; and
5. the prompt-stage disposition: V1 is prohibited, V2A/V2B/V2C are unqualified, and a later prompt
   revision must demonstrate correctness, concise personality-bearing answers, and structural
   stability before freeze.

## Round-close Income audit

Every direct file in `docs/pm_handoff/` remains active and was intentionally retained. The contract,
task boundary, and Gate 1 closure ACK remain governing inputs; `REQUEST-LLM-POC-M4B-MVA-MEASURE-001`
remains open pending dependent efficiency closure; and
`REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002` remains unresolved until Core reviews this revision request.
No incoming file was completed, superseded, deleted, or moved to history in this round.

## Remaining unfinished items

- A qualified personality-bearing prompt; V2A/V2B failed mechanically and V2C failed correctness and
  concise-output review despite passing mechanical checks.
- Core revision/freeze of the changed Reasoner input, encoding fallback, readiness choice, formal
  case set and selection rule.
- Clean-checkout exact-pushed-SHA formal measurements after that freeze; the original five-pair
  matrices remain unexecuted on the revised surface.
- Formal Audio/TTS audible-onset validation and the overall three-second E2E claim.
- Core acknowledgement and revision decisions for this delivery. The accompanying exact pushed SHA
  is reported outside this self-referential document.
