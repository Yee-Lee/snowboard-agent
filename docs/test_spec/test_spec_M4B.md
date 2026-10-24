# M4B Replacement Cognition / Product Test Specification

## 1. Authority, scope and disposition

This is the current Tester-owned specification for the clean M4B replacement approved through
[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md) and amended by the focused
[`TR_spec_M4B_VII`](../reviews/history/TR_spec_M4B_VII.md) ticket-disposal request. It maps the approved behavior in
[`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md) §§2–11 and
[`snowboard.llm/3`](../protocol.md) §4. It retains the affected Foundation contract in
[`m4b_foundation_revision`](../implement/m4b_foundation_revision.md) §§4–8 and its immutable
99-node regression baseline.

Status: **Revised — byte-for-byte POC response-schema and `NeedsDeveloperReview`/aggregate mappings complete;
pending Designer confirmation; no implementation or acceptance result in this document.**

In scope are the listen-only product profile, prompt, constrained-JSON response schema and semantic decoding,
input/admission and explicit ticket-disposal policy,
Conversation lifecycle, memory decisions and SM-authorized planned recovery, private child protocol,
privacy/observability, and the later exact-SHA Pi/human evidence procedure.

Out of scope are the retired action envelope, fresh-Conversation-per-turn behavior, fake prewarm,
fixed `8/48/768`, forced 20-session drift, the former 2s/3s response ceiling, M4C streaming speech,
and unrelated Accepted M4A-only acceptance rows. Deterministic fakes prove control semantics only;
they never establish real-model quality, target memory, or target timing.

## 2. Result, matrix and evidence rules

### 2.1 Result vocabulary

- **Pass**: every required script assertion and forbidden-call assertion passes, all required evidence is
  present, the automatically attested tracked-content/harness/profile/target/evidence identities agree, and the
  required human inspection also passes: USER for #2; Developer for every number and output in #1/#3/#5–#7,
  and focused #4 reasonableness review after automatic validation of its complete raw series.
- **Fail**: an assertion fails, a forbidden call/artifact occurs, a baseline node is missing, a test
  is skipped/xfail/xpass, USER judgment fails a required `M4B-PI-SEM-001` case, or Developer finds any
  unreasonable/inconsistent number or output in #1/#3–#7.
- **Incomplete**: a required measurement, evidence field, identity, raw series, USER result, Developer inspection
  result, or explicit null reason is missing or invalid. Incomplete never converts to Pass.
- **Blocked**: the bound tracked content, target, artifact, credential-free offline setup, or access-controlled
  evidence location is unavailable before execution begins.
- **NeedsHumanReview**: a #2 case has script status Pass and complete captured evidence but no USER verdict for
  that exact case attempt yet. It is not Pass and cannot be designated by final `PV` aggregation.
- **NeedsDeveloperReview**: #1 or #3–#7 has script status Pass and complete evidence but no complete Developer
  review bound to that exact Test-ID result yet. It is not Pass and cannot be designated by final `PV`
  aggregation.

Test/function counts are not an acceptance criterion. A table-driven function may cover many rows
only when its result preserves the Test ID, case ID and assertion-level outcome.

`PV` has one final disposition over seven independently executable Pi Test IDs. Scripts determine assertion-level
results for all seven IDs. USER inspects #2 answer meaning; Developer inspects every recorded number and output for
#1/#3/#5–#7 and #4's boundaries, extrema, anomaly/stop records, formula and digests after complete automated
point validation. Both applicable layers must Pass. Any Fail, missing or
Incomplete designated result prevents `PV` Pass; a
pre-execution Blocked attempt supplies no `PV` credit. Each Test ID has a fresh setup, unique sub-run ID, private
and public evidence partition and independent outcome. No transcript, state, event, series, card or completion
flag from one Test ID is an input to another. Only the protected tracked-content/harness/profile/target/artifact
tuple and the aggregate `PV` identity are shared.

Every product-executing command is the smallest rerun unit and owns a new sub-run/attempt identity plus empty
private/public partitions. A failed single-command Test ID reruns alone; within `M4B-PI-SEM-001`,
`M4B-PI-WAKE-001` and `M4B-PI-RES-001`, only the failed independently commanded case reruns. Per-Test-ID case
aggregation launches no product behavior. Superseded attempts remain visible but cannot satisfy the designated
result, and the protected tuple remains byte-identical. A stopped, failed, Blocked or Incomplete
`M4B-PI-MEM-001` sub-run publishes no threshold estimate; another Test ID's result neither supplies nor invalidates
an independently complete measurement result.

### 2.2 Execution matrix

| Matrix ID | Layer | Required environment | Timeout policy |
| :--- | :--- | :--- | :--- |
| `PU` | portable unit | Declared Python range `>=3.11,<3.14`; Linux x86_64/aarch64 and macOS arm64; pure Python; no native/model/network | 60 s per Test ID |
| `PI` | portable integration | Same Python/platform range; deterministic adapter/tokenizer/sampler/action fakes | 90 s per Test ID |
| `PS` | portable subprocess | Linux x86_64/aarch64 on Python 3.13; fake child in a real POSIX process group | 120 s per Test ID |
| `PV` | Pi product verification | Raspberry Pi 5 4 GB, Debian 13 aarch64, target CPython 3.13.5; one new aggregate run ID and newly empty private/public roots; automatically attested tracked-content, harness, null-threshold measurement-profile, target and artifact tuple; seven fresh independent sub-runs; USER inspects #2 answer meaning; Developer inspects every value/output for #1/#3/#5–#7 and focused audited results for #4 | 60 min per Test-ID sub-run; product watchdogs remain 45/30/2/2/1 s; every command has a bounded harness timeout |

`PV` initialization creates the aggregate identity and empty root pair but launches no test. Each Test ID then runs
from its own exact command in §5, may execute in any order, creates a new `sub_run_id` and fresh Product Session
where applicable, and writes only its own private/public partition. Scripts evaluate #1–#7. `M4B-PI-SEM-001` is
the only USER-inspected Test ID; #1/#3/#5–#7 require complete Developer value/output inspection, while #4
requires complete automatic point audit followed by focused Developer reasonableness inspection. No Test ID waits
for, imports or validates another ID's evidence. A failed item
reruns by itself; unaffected designated results remain valid only while the protected tuple is unchanged.
Finalization reads the seven designated script results plus their applicable USER/Developer inspection results
solely to aggregate the one `PV` disposition.

Initialization and every sub-run reject pre-existing output in their target partition and any earlier PM/PR/PH
profile, threshold, partial series, card, transcript, status or digest. No role approval, reviewer identity,
signature or freeze file is an execution input.

USER runtime disposition (2026-09-12): macOS arm64 is diagnostic-only for the current M4B portable
candidate. Formal portable sign-off requires the Linux CPython 3.11/3.12/3.13 matrix; Darwin-only
process-group and CPython 3.11 hardware-diagnostic cancellation failures do not reject the candidate.
Diagnostic exclusions are applied by the execution profile and are not implemented as committed
`skip`/`xfail` controls in protected tests.

Timeouts prevent hangs; they are not response-time PASS ceilings. A timeout is Fail unless the
case explicitly tests a watchdog and observes the required bounded cleanup terminal.

### 2.3 Synchronization and fakes

All async and concurrent cases use named `asyncio.Event`, pipe/queue acknowledgement, child terminal,
task-join, action-complete, close-proof, recovery-ticket and RM-READY barriers. Correctness sleeps,
poll-until-lucky loops and timing-order assumptions are forbidden. Fakes expose call ledgers and fail
if an unexpected model, mutation, speech, recovery, network, file-write or next-request call occurs.

### 2.4 Evidence locator contract

The later runner supplies two existing, access-controlled roots:

- `<public_root>/<candidate_sha>/`: sanitized JUnit, result cards, identity/digest summaries and the
  evidence index.
- `<private_root>/<candidate_sha>/`: raw prompts/answers, process telemetry and memory/timing series;
  never copied into Git or public cards.

Every result record contains `schema_version`, `test_id`, `case_id`, `candidate_sha`, `profile_id`,
`profile_sha256`, matrix/platform/Python identity, start/end monotonic timestamps, `status`, and
`evidence_sha256`. PV records additionally preserve `script_status` and exactly one applicable inspection result:
`user_result` for #2 or `developer_review` for #1/#3–#7. The Developer review contains a per-field checklist and
concise anomaly notes, but no reviewer identity, signature, approval token or timestamp gate. Missing or mismatched
identity or inspection evidence is Incomplete/Fail. Portable results are located at
`<public_root>/<sha>/portable/<TEST-ID>.{junit.xml,json}`. Pi structural cards are at
`<public_root>/<sha>/cards/<TEST-ID>.json`; human rubrics are at
`<public_root>/<sha>/human/<TEST-ID>.json`; sanitized manifests name private artifacts only by digest
and opaque locator. No card may contain private text, IDs, absolute paths or IPC payloads.

### 2.5 PV result state, inspection record and aggregation

Every Pi case or single-command Test ID first produces `script_status`, restricted to
`Pass | Fail | Incomplete | Blocked`. Script evaluation never writes the final human-inspected Pass by itself.
The externally visible Test-ID/case `status` transitions are exact:

| Scope | Script result | Required next state / terminal result |
| :--- | :--- | :--- |
| #2 semantic case | `Pass` | `NeedsHumanReview`; exact-attempt USER verdict changes it to `Pass` or `Fail` |
| #1/#3/#4/#6 single-command Test ID | `Pass` | `NeedsDeveloperReview`; exact-result Developer review changes it to `Pass` or `Fail` |
| #5/#7 case collection | every designated case script `Pass` | case aggregation writes Test-ID `script_status=Pass`, `status=NeedsDeveloperReview`; one complete per-Test-ID Developer review changes it to `Pass` or `Fail` |
| any scope | `Fail | Incomplete | Blocked` | same unsatisfied status; a human result cannot override it |

For #2, each USER result binds `pv_run_id`, `test_id`, `case_id`, `case_attempt_id`, protected-tuple digest and
captured-result-card digest. All three exact cases must have script Pass and USER Pass before
`M4B-PI-SEM-001` is Pass. A rerun creates a new attempt/card digest and invalidates the earlier case verdict for
selection without altering completed siblings.

For #1/#3/#5–#7, the script creates a private inspection catalog that enumerates every numeric field, raw-series
row, trace row, terminal/output record and null reason by stable locator. For #4, the private catalog may instead
enumerate the complete-series digest/count, validation coverage/count, lifecycle boundaries, extrema with source
point locators, stop/anomaly records, formula inputs/outputs and null reasons; it must not claim a complete audit
from a sampled subset. Both catalog forms bind the digest of the complete underlying evidence.
Developer review is one per Test ID and contains exactly:

- `schema_version`, `pv_run_id`, `test_id` and the protected-tuple digest;
- designated script result-card locator and SHA-256;
- inspection-catalog locator and SHA-256;
- expected/reviewed field and row counts, which must be equal and nonzero;
- private evidence-manifest locator and SHA-256 covering the complete inspected values/outputs;
- `status=Pass|Fail`, exact failed case/field locators when Fail, and concise anomaly notes.

It contains no reviewer identity, signature, authorization, approval token or timestamp gate. A review with a
missing catalog item, unequal count, stale card/evidence digest, wrong tuple/Test ID, or inaccessible private
locator is Incomplete. Review Fail makes that Test ID Fail and identifies the exact single-command sub-run or
WAKE/RES case to correct or rerun. Replacing any designated case/card invalidates the prior per-Test-ID review and
returns a script-Pass result to `NeedsDeveloperReview`.

`aggregate-cases` evaluates only the designated case-script cards for #5/#7. It neither records nor infers the
Developer review and cannot emit final Test-ID Pass. `finalize` selects no `NeedsHumanReview`,
`NeedsDeveloperReview`, stale, superseded, wrong-tuple or partially merged result. It reports aggregate `Pass` only
when all seven script statuses Pass, all three exact #2 USER verdicts Pass, and all six exact #1/#3–#7 Developer
reviews Pass. An applicable human Fail produces aggregate Fail; a missing/incomplete human record produces the
corresponding Needs state/Incomplete and never Pass.

## 3. Portable specification catalog

| Test ID | Exact authority and risk | Layer / matrix | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4B-NORM-001` | Product §§3.1–3.2, §§5.1–5.2, §6; unsupported or over-limit input mutates Conversation or publishes R1 before ticket disposal | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-NORM-001.*` |
| `M4B-PROMPT-001` | Product §§2.1–2.2, §4.1, §9; mutable prompt/schema/profile or forbidden regex/GBNF path changes product identity and real-model behavior | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-PROMPT-001.*` |
| `M4B-SEM-001` | Product §4.1 and §6; invalid `text/end` or spoken length reaches action | `portable unit` (`PU`); 60 s | `portable/M4B-SEM-001.*` |
| `M4B-S2-001` | Product §4.2; protocol §§4.5, 4.7; unsafe/revised partial text escapes parser | `portable unit`, `portable subprocess` (`PU,PS`); 60/120 s | `portable/M4B-S2-001.*` |
| `M4B-ADM-001` | Product §§5.1–5.2, §7; protocol §§4.3–4.5; MEASURE/disposal mutation, private retention or stale/discarded ticket admits the wrong request | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-ADM-001.*` |
| `M4B-PREFILL-001` | Product §5.2; fresh listen-only prefill tier confused with multimodal or 1024 context | `portable integration` (`PI`); 90 s | `portable/M4B-PREFILL-001.*` |
| `M4B-OUTCOME-001` | Product §§5.2, 6 and 7.2; wrong speech owner, disposal ordering, route or fallback changes user-visible behavior | `portable integration` (`PI`); 90 s | `portable/M4B-OUTCOME-001.*` |
| `M4B-CONV-001` | Product §7.2; Foundation §§4–8; history/replacement leaks or session/turn identity resets | `portable integration` (`PI`); 90 s | `portable/M4B-CONV-001.*` |
| `M4B-MEM-001` | Product §5.3, §§9–10; incorrect threshold order/sample policy sends unsafe work | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-MEM-001.*` |
| `M4B-REC-001` | Product §5.3; Foundation §7; `AR_impl_M4B_IV`; adapter schedules before SM authorization or recovery failure resumes admission | `portable integration` (`PI`); 90 s | `portable/M4B-REC-001.*` |
| `M4B-WIRE-001` | Product §§5.1, 8–9; protocol §§4.3–4.7; desync/disposal/proof failure leaks child or permits illegal state | `portable subprocess` (`PS`); 120 s | `portable/M4B-WIRE-001.*` |
| `M4B-PRIV-001` | Product §§5.1, 10; protocol §§4.1, 4.3–4.4; rejected private input survives disposal or escapes observability boundaries | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-PRIV-001.*` |
| `M4B-REG-001` | Product §§11.1(11), 11.2; Foundation `FND-REG-001`; tests are deleted/weakened, unrelated M4A acceptance is substituted, or PV review/aggregate states grant false Pass | `portable integration` (`PI`); 180 s suite cap | `portable/M4B-REG-001.*` |

## 4. Portable cases and acceptance criteria

### M4B-NORM-001 — Listen projection, normalization and input limits

Fixture: a ledger-backed Conversation fake starts at revision `r`, plus exact deterministic tokenizer
counts. `MEASURED`, `DISCARDING`, `TICKET_DISCARDED`, `GENERATE`, state mutation, R1 publication and
model-content capture each have separate barriers.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `N01` | One matching `listen/ok`; compatibility characters, mixed Unicode whitespace and edge whitespace | NFKC first, maximal whitespace run becomes one U+0020, edges removed; model content is exactly normalized text; envelope/private IDs never serialized |
| `N02` | TAB/LF/CR whitespace | Accepted then collapsed; counted spaces remain code points |
| `N03` | NUL, surrogate, and each non-whitespace `Cc` class representative | E1 before MEASURE; revision/call ledgers unchanged; no application retry Fact |
| `N04` | Non-`str` text | E1 before normalization/tokenization; zero model calls |
| `N05` | Empty or all-whitespace `ok`; `timeout`; `error` carrying hostile `text/extra` | Exact no-input R1 response; timeout/error payload ignored and absent from logs; no MEASURE/GENERATE/mutation |
| `N06` | Normalized 20 then 21 code points, including spaces and non-BMP symbol | 20 proceeds to token admission; 21 returns exact input-limit R1; no truncation/partial send; Python code-point count used |
| `N07` | Codepoint-valid fake tokenizer results 32 then 33 direct-user tokens | 32 may proceed; 33 enters `MEASURED → DISCARDING`, clears normalized-text local, obtains an exact all-true `TICKET_DISCARDED`, clears snapshot, and only then publishes exact input-limit R1; same session/generation/revision/history/KV; zero GENERATE/native send/semantic mutation |
| `N08` | zero/multiple items; `read/look`; pending external input; wrong session/turn; unknown status; listen/speak capability false | Every row is `UNSUPPORTED_INPUT` E1; no model, mutation or normal `LLMResponse` |

### M4B-PROMPT-001 — Frozen profile, prompt bytes and response-schema identity

Fixture: canonical byte constants, a tokenizer double that records exact bytes, strict profile/lock and
response-schema loader, READY verifier, and a native response-format seam that records which LiteRT-LM factory is
called. Startup side effects are latched behind an authentication barrier.

The exact expected byte composition is the UTF-8 encoding of these two strings with no separator,
BOM or trailing newline:

```text
你是「雪板」繁體中文語音助理，只能聽與說，不能看或使用工具。只輸出含 text、end 的 JSON。一般回答的 text 不超過30字且 end=false；明確要求結束時 end=true。語氣：
溫暖自然，稍帶幽默。
```

The exact response-schema locator is `requirements/m4b/semantic-output-v1.schema.json`. Its content is the
following 352-byte UTF-8 sequence, including the final LF and without BOM; SHA-256 is
`796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:snowboard:m4b-mva:semantic-output:v1",
  "title": "M4B-MVA compact semantic output",
  "type": "object",
  "additionalProperties": false,
  "required": ["text", "end"],
  "properties": {
    "text": {"type": "string", "maxLength": 4096},
    "end": {"type": "boolean"}
  }
}
```

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `P01` | Load canonical core, personality and concatenation | Exact UTF-8 bytes, no BOM/newline; SHA-256 equals `8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec`, `57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5`, `872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643`; selected tokenizer counts exactly `57/9/66` |
| `P02` | Insert/remove/change one byte, BOM/newline, personality suffix or YAML override | Fail before child spawn/native import; no fallback/default or user suffix |
| `P03` | Authenticate full product profile, artifact lock, deployed response schema and READY | Exact profile/candidate/pairing/runtime/model/ABI, `temperature=0.0`, `top_p=1.0`, threads 4, reserve 128, context 1024, wire 3 and offline flags match field-by-field. Startup reads the exact logical locator `requirements/m4b/semantic-output-v1.schema.json`; its deployed content is exactly 352 UTF-8 bytes with final LF/no BOM and SHA-256 `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`. Profile, artifact lock and READY repeat that locator and digest exactly; the decoded mapping equals the POC schema above. Matching only an overall profile digest, embedding a replacement object or trusting a digest constant without checking the deployed bytes is insufficient |
| `P04` | Extra/missing/alternate profile, endpoint, artifact, system-site dependency or prewarm option | Startup failure with zero child/model/network side effect; POC provenance digest cannot stand in for product identity |
| `P05` | Raw-JSON and decoded-mapping corpus with legal lexical variations and one-field mutations | Raw JSON accepts both member orders and representative legal insignificant whitespace and decodes them to the same semantic value; duplicate/unknown/missing members, wrong types, multiple top-level values, trailing non-whitespace bytes and invalid UTF-8/escape are rejected. An already-decoded mapping is validated directly without re-serialization, accepts either insertion order, and never fabricates claims about duplicate or lexical bytes the runtime did not expose |
| `P06` | Real profile with read, look, tool or external-message input enabled; then generic mock profile with its accepted capabilities | Every real mismatch fails before factory side effects; generic mock behavior remains accepted and is not narrowed |
| `P07` | Real composition missing schedule/wait/sampler seam, or mock composition receiving one; equivalent YAML keys | Real requires all three narrow injected interfaces; mock requires all three null; YAML cannot obtain them |
| `P08` | Four deployment paths missing/non-absolute/non-file, wrong profile ID, or any nonfinite/nonpositive watchdog | Strict failure before workdir/native/child/sampler/RM side effect; exact valid fields proceed |
| `P09` | Exercise the native response-format seam and then substitute regex, GBNF, prefix, an embedded object, wrong locator, missing/final-LF or BOM variant, one-byte mutation, stale digest, or forbidden schema keyword | Production verifies deployed bytes before decoding and calls `ResponseFormat.json` exactly once with the exact decoded POC mapping. The native mapping contains only its declared object/member/type constraints and `text.maxLength=4096`; it contains no `oneOf`, `if/then/else`, `const`, `minLength`, `pattern` or other `text/end` relationship. Regex/GBNF/prefix factories are never called. Any alternate factory or source/profile/lock/READY/deployed-copy locator, byte, length or digest mismatch fails before native import/credited behavior with zero fallback or prompt-only acceptance |

### M4B-SEM-001 — Terminal semantic validation

Fixture: the exact decoded native POC schema mapping, decoded-object Python terminal validator and shared
`ActionPayloadValidator`; no real model. The native schema enforces structure and `text.maxLength=4096`; every
`text/end` relationship, normalization rule and 30-spoken-character rule below is a separate fail-closed Python
semantic check and must not be added to or substituted for the native schema.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `S01` | all four wire `text` empty/non-empty × `end` false/true combinations | All four satisfy the exact native structural schema. Python terminal validation accepts non-empty/false, non-empty/true and empty/true; empty/false is `INVALID_SEMANTIC`, never reaches action/speech and fabricates no text. No conditional/minimum-length native keyword supplies this result |
| `S02` | JSON escapes for quote, slash, backslash, BMP/non-BMP Unicode and split surrogate escape pair | Decode exactly once, normalize once, preserve action punctuation; malformed/lone escape rejected |
| `S03` | output containing NUL, surrogate or disallowed control after decoding | Invalid semantic; never reaches action/speech |
| `S04` | 30 then 31 countable characters with whitespace/punctuation interspersed | 30 accepted, 31 rejected, no truncation; letters/numbers/symbols/emoji count, whitespace and Unicode category `P*` do not |
| `S05` | `「你好嗎？」` and `嗨🙂！` | `spoken_length` is exactly 3 and 2 respectively |
| `S06` | Valid semantic payload then deliberate action-schema mismatch | Same validator instance used by Reasoner and SM; mismatch is E1 before publication |
| `S07` | Non-empty wire strings consisting only of collapsible whitespace, for `end=false` and `end=true` | Both normalize to empty exactly once; false is `INVALID_SEMANTIC` and takes the existing R2 cleanup/replacement path with zero retry/replay, while true is the valid model-owned silent end and reaches direct rest/`END_SESSION` |

### M4B-S2-001 — Incremental UTF-8/JSON extraction

Fixture: byte-chunk matrix feeds the real incremental parser. A fragment barrier captures every
`SAFE_TEXT`; Speak/TTS ledgers remain armed to detect forbidden dispatch.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `X01` | Every byte boundary of valid multi-byte UTF-8 JSON objects in both member orders and with representative legal insignificant whitespace, then fully coalesced input | Same terminal semantic object and ordered non-empty fragments for every partition; partial UTF-8 never emitted; when `end` precedes `text`, the parser may wait but must not reject the legal order |
| `X02` | Split before/inside escape sequences and escaped Unicode across both member orders | JSON syntax/escape bytes withheld; emitted text is decoded semantic content only |
| `X03` | Parser emits multiple fragments | Sequence begins 0 without gaps/duplicates; concatenation is exact prefix of normalized terminal text; fragments never revised |
| `X04` | Prefix mismatch, fragment after terminal, duplicate/late terminal, invalid terminal or trailing bytes | Protocol/semantic E1; generation/TTS path cancelled; no successful RESULT/Facts |
| `X05` | Valid fragments in M4B full-response mode | First-safe time recorded, but zero Speak/TTS dispatch until validated terminal result; M4C streaming behavior not claimed |
| `X06` | Parser delays fragments at punctuation/24-codepoint boundary or emits none before terminal | Both are legal when terminal/prefix proof succeeds; no fixed fragment count or latency assertion is introduced |
| `X07` | Empty wire text and non-empty-but-normalizes-empty terminal text, each with `end=false` and `end=true` | No `SAFE_TEXT` or fabricated text is emitted. False is rejected and reaches the existing R2 cleanup path with zero retry/replay; true completes as a valid empty semantic terminal and maps to silent end/rest |
| `X08` | Runtime returns an already-decoded exact mapping and exposes no output chunks | Validate the mapping directly and permit zero pre-terminal fragments; no re-serialization, invented lexical assertion or switch to regex/GBNF/prefix encoding is allowed |

### M4B-ADM-001 — Non-mutating admission, ticket binding and explicit disposal

Fixture: child Conversation exposes generation/revision/history/KV/token-count/native-scratch/output-allocation
snapshots, live-object probes and a renderer/native-send call ledger. Parent Reasoner exposes normalized-text,
snapshot, Fact-publication and outbound-frame barriers. `MEASURED`, `DISCARDING`, scrub return,
`TICKET_DISCARDED`, R1 publication, CLOSE and GENERATE are released independently.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `A01` | MEASURE on clean Conversation with unique private canary | Same tokenizer/renderer as generation; exact non-negative fields returned; generation/revision/history/KV/output allocation/native-send unchanged; before MEASURED, Python request/tokenizer temporaries are gone and ticket ledger retains only opaque ticket, identities, input digest, revision and integer counts; native `last_rendered_message` is the sole permitted child-side private-text retention |
| `A02` | Equation totals 896+128=1024 then 897+128=1025, including alternate splits of current/incremental | Inclusive 1024 passes token equation; 1025 returns context R2 before mutation/send; reserve/context fixed 128/1024 |
| `A03` | Negative, boolean, float, overflow/impossible or internally inconsistent metric | Protocol E1 before inference; no coercion |
| `A04` | matching latest ticket and identical text/digest/revision/generation | GENERATE consumes ticket once before native send; successful RESULT increments revision exactly once |
| `A05` | missing, reused, explicitly discarded, stale-revision, wrong-generation, wrong-session, wrong-input-digest or text-mismatch ticket used for GENERATE | E1, zero additional native send and zero mutation; discarded ticket remains permanently invalid even after a later successful MEASURE |
| `A06` | CLOSE from MEASURED with one outstanding ticket | CLOSE destroys ticket and native scratch with Conversation cleanup, returns only the existing all-three true close proof, and later ticket use is rejected; no separate TICKET_DISCARDED is fabricated |
| `A07` | Codepoint-valid 33-token MEASURE, then exact DISCARD_TICKET | Reasoner releases normalized-text local before constructing the snapshot-only frame; request exact-matches new request ID plus session/generation/revision/ticket/input digest; state is `MEASURED → DISCARDING`; renderer is invoked exactly once with `__M4B_TICKET_SCRUB__`; native scratch becomes the fixed scrub rendering; token count, generation, revision, semantic history and KV are byte/value unchanged; zero runtime clear API, GENERATE or native send |
| `A08` | Exact TICKET_DISCARDED after scrub barrier | Terminal repeats exact request/session/generation/revision/ticket/digest, has `native_render_scrubbed=true`, `ticket_invalidated=true`, `private_input_erased=true`, `conversation_state="ready"`; ticket metadata is cleared, no live child/native object retains rejected text, Reasoner releases snapshot, state becomes CONVERSATION_READY, then and only then R1 publishes |
| `A09` | After A08, new short input on same Conversation | New MEASURE and normal GENERATE succeed with unchanged starting generation/revision/history/KV from before rejection; old ticket is still rejected |
| `A10` | Three 33-token rejection/disposal cycles followed by a short input | Every cycle has a distinct exact ticket/discard request and acknowledged cleanup before its R1; same Conversation/revision throughout rejects; final short turn generates normally; no count-based replacement/escalation |
| `A11` | Scrub renderer raises, returns invalid rendering, changes token count or leaves canary reference | E1, no TICKET_DISCARDED/R1/GENERATE/native send; bounded PGID destruction proof required |
| `A12` | Independently mismatch request/session/generation/revision/ticket/digest; stale/duplicate discard; independently false/missing each of the three proofs; extra/malformed/wrong terminal; timeout or EOF, including lost ACK after actual invalidation | Every row is E1, never R1; no terminal substitution or retry; actual child invalidation without an exact observed ACK is insufficient; bounded PGID cleanup and waitpid proof before further admission |
| `A13` | Compare public SM state, Event/Fact unions and `LLMResponse` schema before/after disposal support | Disposal remains private adapter/protocol control; no public state, Event, Fact or `LLMResponse` field/variant is added or emitted |

### M4B-PREFILL-001 — Fresh listen-only prefill tier

Fixture: a newly OPENED generation at revision zero, one normalized listen within both direct limits,
and measured rows at 128 and 129 runtime-prefill tokens.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `F01` | fresh row with `runtime_prefill_tokens=128` and otherwise valid equation | Profile tier passes and admission continues to memory decision |
| `F02` | identical row with `runtime_prefill_tokens=129` | Product-profile E1, not input/context R1/R2; no GENERATE |
| `F03` | second normal turn or non-listen/additional future projector | Fresh listen tier is not applied as a general ceiling; unsupported M4B projector still fails under `N08` |
| `F04` | valid 128 prefill but total equation >1024; valid total but direct tokens 33 | Independent context/input rule still fails; 128 never grants multimodal input or replaces 1024/32 limits |

### M4B-OUTCOME-001 — Canonical policy matrix

Fixture: parameterized Reasoner with mutation ledger, sampler, semantic result/failure and capability
fakes; SM/action completion barriers assert phase order. Every row validates the exact four-field
`LLMResponse` and exact Traditional Chinese application text from product §6.

| Case family | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `O01` | timeout/error/empty, codepoint-limit, then measured token-limit rows | exact application-owned `我沒聽清楚，請再說一次。` or `這句有點長，請縮短後再說一次。` respectively, with `speak + KEEP_NEXT + ("listen",)`; codepoint rejection performs no MEASURE, while token rejection publishes only after exact TICKET_DISCARDED; generation/revision/history/KV unchanged and zero model mutation |
| `O02` | context equation failure | exact `對話內容已滿，請再說一次。` + `REPLACE_NEXT`; zero rejected-input send/replay |
| `O03` | memory blocks generation but permits notice | exact `系統需要整理，請稍後再試。` + `END_SESSION`; zero model generation; final primary speech then exactly one rest |
| `O04` | memory blocks notice | `rest {}` + `END_SESSION`; zero TTS and generation; exactly one rest |
| `O05` | model non-empty/false | model text owns speech payload; `KEEP_NEXT`; no application paraphrase or second inference |
| `O06` | model non-empty/true | model text spoken, then exactly one rest and `END_SESSION`; primary/rest records never overlap |
| `O07` | model text empty after normalization, once with each `end` boolean | true produces direct `rest {}` + `END_SESSION` with no fabricated speech; false produces exact application-owned `剛才沒有成功，請再說一次。` + `REPLACE_NEXT` after the proven R2 cleanup barrier with zero retry/replay |
| `O08` | each allowed REQUEST_FAILED code with terminal proof and usable Engine | exact `剛才沒有成功，請再說一次。` + `REPLACE_NEXT`; tainted generation closed; no replay |
| `O09` | two and three consecutive proven replaceable failures | identical R2 each time; no count escalation to R3/E1 |
| `O10` | button interrupt | no normal cognition Fact; R3 convergence |
| `O11` | unsupported input, mismatch/desync/crash/unusable backend/missing proof/unavailable Speak | no normal response or silent downgrade; E1 and Level 1/2/3 path |
| `O12` | token-limit discard held at scrub/terminal barrier, then failed or released | While held, zero R1 Fact/action; failure takes E1 with no normal Fact; only exact acknowledged disposal releases one canonical input-limit R1 |

### M4B-CONV-001 — Conversation continuity and replacement

Fixture: one Product Session with a fake Conversation holding visible turn markers. Barriers are
`action_done`, `request_joined`, `close_proven`, `open_ready` and `next_perception_allowed`.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `C01` | two successful normal turns | same child, Conversation object, generation and increasing revision; second fake response proves first-turn context was present |
| `C02` | context reject before native send | old revision/history unchanged; action completes before close; rejected input absent from old/new Conversation |
| `C03` | successful replacement | exact order block admission → request terminal/join → close all-three proof → generation+1 → clean open → READY → next perception; never two claims |
| `C04` | first repeated request after replacement, then following turn | user repeats explicitly; request succeeds on new generation; subsequent normal turn also succeeds; system never auto-replays |
| `C05` | replacement across action error/success | preselected normalized/default perceptions preserved; same Product `session_id`; monotonic `turn_id` never resets/reuses; no buffer flush/discard |
| `C06` | stale session/generation/correlation/task completion | dropped with sanitized diagnostic; active generation/session unchanged |

### M4B-MEM-001 — Memory decision and release-profile policy

Fixture: injected release profile thresholds `0 < S <= G`, unique-PID sampler snapshots and independent
model/TTS/recovery ledgers. Values are synthetic and cannot claim Pi memory acceptance.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `M01` | For `S<G`, MemAvailable `G`, `G-1`, `S`, `S-1`; then a valid `S==G` profile | `G` and above GENERATE; `[S,G)` exact notice/end; below `S` silent rest/end; equal thresholds are accepted and have no notice band; comparisons are strict `<`; exactly one healthy unique-PID sample is taken immediately before permitted GENERATE |
| `M02` | sampler exception/identity loss, duplicate PID, inconsistent totals, OOM, throttling or invalid temperature sample; separately, otherwise healthy consecutive samples with increasing swap used and unchanged `MemAvailable >= G` | health/identity faults are E1 with no send/TTS/recovery scheduling; swap growth alone is recorded and must not raise E1 or alter the `M01` GENERATE decision |
| `M03` | measurement profile through normal AppConfig; release null/nonpositive/reversed thresholds | fail before composition side effects; only dedicated measurement loader accepts null thresholds |
| `M04` | YAML/source attempts to set threshold/sampling/prompt/response-schema/context/offline values | unknown/rejected; canonical profile remains unchanged |
| `M05` | legacy `product_config_path`, recycle keys or literal fixed 8/48/768 policy | strict rejection before spawn; no compatibility alias |

### M4B-REC-001 — Planned-recovery authorization and supervision

Fixture: real SM convergence logic with fake Adapter and RM seams. The fake records
`mark_pending`, primary/rest terminal, close proof, SM authorization, schedule, wait and READY. Each
step is held by an explicit barrier.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `R01` | memory capacity result | Adapter atomically marks one `RECYCLE_PENDING`; zero `ScheduleRecovery` calls at mark time |
| `R02` | matching close/cleanup proof arrives while primary action or rest is held | cleanup proof alone schedules zero recovery |
| `R03` | release primary/rest terminal after full proof | SM authorizes exactly one same-key recovery in private post-close phase; Adapter/composition invokes seam only after authorization |
| `R04` | hold recovery wait before RM READY | session tracking retained, wake admission blocked, state not IDLE, new/open requests and ticket waiters do not proceed |
| `R05` | RM returns matching READY | barrier releases once; session clears/resumes wake/IDLE only afterward; defensively waiting next open can now succeed |
| `R06` | RM timeout, exception, wrong key/identity or unusable replacement | Level 3; no next request, no stranded ticket waiter, no false READY/normal Fact |
| `R07` | duplicate close/notice/authorization | one recovery maximum; stale duplicate rejected without state change |

### M4B-WIRE-001 — `snowboard.llm/3` state, proof and process cleanup

Fixture: actual fake child subprocess with PID=PGID, controllable descendants and bytewise framing.
Parent/child request and process-exit barriers replace sleeps.

| Case family | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `W01` | exact READY then each missing/extra/mismatched field | exact READY enters ENGINE_READY with no Conversation; any mismatch terminates/kills and waitpids whole PGID; no fallback |
| `W02` | OPEN/OPENED and OPEN_REJECTED proof matrix | identity/revision/state exact; clean rejection requires cleanup+usable; false proof is E1 |
| `W03` | MEASURE/MEASURED and GENERATE/SAFE_TEXT/RESULT | legal `CONVERSATION_READY → MEASURING → MEASURED → GENERATING → CONVERSATION_READY` transitions, request/session/generation/revision/ticket/metrics exact; RESULT only after native join/prefix proof |
| `W04` | each allowed REQUEST_FAILED code and every false/unknown variant | only true terminal proof + usable Engine enters TAINTED/R2; otherwise E1/cleanup |
| `W05` | CANCEL once during OPEN/MEASURE/GENERATE/CLOSE, with deferred and proof matrices | exact allowed operation/state mapping excludes DISCARD_TICKET; second/mismatched cancel rejected; cancelled CLOSE incomplete proof escalates; no fabricated terminal or normal cognition Fact |
| `W06` | CLOSE each legal reason and proof combination, including from MEASURED | only all-three true returns ENGINE_READY/none; MEASURED close destroys outstanding ticket/native scratch with Conversation cleanup and later use fails; no TICKET_DISCARDED is fabricated; invalid reason/proof is E1 |
| `W07` | SHUTDOWN from ENGINE_READY versus active Conversation/request | READY-only ACK, child zero exit and waitpid; active shutdown rejected except after Level 2 destruction |
| `W08` | wrong order, BUSY/reentry, malformed/overlong framing, invalid JSON/UTF-8, EOF, duplicate/late/output-after-terminal | deterministic protocol §4.7 E1, admission blocked, sanitized diagnostic, bounded PGID cleanup |
| `W09` | child ignores TERM and owns nested descendant; then RM recovery | TERM→KILL bounded waits prove owner and descendants gone; successful fully attested new child handles OPEN/MEASURE/GENERATE/CLOSE |
| `W10` | Exact DISCARD_TICKET/TICKET_DISCARDED exchange after MEASURED | Exact request/session/generation/revision/ticket/digest and all three true proofs; `MEASURED → DISCARDING → CONVERSATION_READY`; fixed scrub renderer called once, token count unchanged, ticket cleared/permanently invalid, no GENERATE/native send/runtime clear |
| `W11` | Each discard request identity mismatch; stale/duplicate; scrub/render/count failure; false/missing proof; malformed/wrong terminal; timeout/EOF | E1 from MEASURED or DISCARDING, never R1; no success terminal accepted; parent terminates/kills and waitpids PGID before admission/recovery |
| `W12` | CANCEL or OPEN/MEASURE/DISCARD/GENERATE/CLOSE/SHUTDOWN during DISCARDING; racing interrupt | DISCARDING accepts no command or CANCEL; reentry is E1. Interrupt waits for exact disposal terminal and then converges, or timeout/EOF takes the same bounded E1 PGID-cleanup boundary; no normal R1 races ahead |

### M4B-PRIV-001 — Redaction and independent dashboards

Fixture: canary transcript/prompt/raw JSON/semantic/fragment/session/path/IPC values injected through
success and every error path; live-object probes cover parent locals, child Python temporaries, ticket
ledger and native render scratch; log/evidence/workdir scanner runs after disposal and cleanup barriers.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `V01` | success, validation error, child stderr, exception and cleanup | no canary/private value or reversible encoding in logs, exceptions, public cards or dashboards; only allowed digest/profile/candidate/version/code/counters/proofs |
| `V02` | prompt composition evidence | once-per-profile row contains only profile ID, exact three counts/hashes; not copied into per-turn prefill |
| `V03` | runtime/context evidence | exact §10.2 fields, projected total consistent, no prompt or semantic text |
| `V04` | memory evidence | unique-PID owner/system fields and lifecycle point complete; open delta not added again to combined peak |
| `V05` | timing with missing/not-applicable first-safe/TTS/audio node | one monotonic domain; explicit null plus stable reason; no wall-clock reconstruction, PASS ceiling or audible-onset claim |
| `V06` | post-close filesystem/process scan | no transcript, prompt, output, IPC payload, temp workdir or orphaned private content remains |
| `V07` | 33-token canary through MEASURED and acknowledged disposal | Before MEASURED, child request/tokenizer temporaries are absent and only native scratch may retain canary; before DISCARD_TICKET, Reasoner normalized-text local is absent and frame contains snapshot fields only; before R1, snapshot/ticket binding are gone, native scratch contains only fixed scrub rendering and no live parent/child/native object retains canary |
| `V08` | Inspect ticket ledger and scrub call | Ledger never retains raw input, rendered content or private IDs beyond protocol-required opaque identity/digest fields; scrub input is exactly public `__M4B_TICKET_SCRUB__`, called once, not logged as private evidence and never sent to model |
| `V09` | Every disposal failure/timeout/EOF followed by bounded destruction | No R1/public success artifact, rejected canary or stale ticket survives in live objects, sanitized evidence, replacement child or post-cleanup filesystem; forensic zeroization of freed allocator capacity is explicitly not claimed |

### M4B-REG-001 — Retained coverage and anti-weakening

The immutable Foundation baseline is exactly
[`baselines/m4b_foundation_node_ids.txt`](baselines/m4b_foundation_node_ids.txt), currently 99 sorted
node IDs. Candidate verification uses the following fail-closed comparison, with commands executed
from the clean candidate checkout:

```bash
regression_files=(
  tests/milestones/test_m1_foundation.py
  tests/milestones/test_m2_mock_pipeline.py
  tests/test_events.py
  tests/test_state_manager.py
  tests/test_m2_sm_flows.py
  tests/test_m2_flows.py
  tests/test_m2_wrk_003.py
)
PYTHONPATH=src pytest -o addopts='' --collect-only -q "${regression_files[@]}" \
  > /tmp/m4b_foundation_post_collection.txt
awk '/::/' /tmp/m4b_foundation_post_collection.txt | LC_ALL=C sort -u \
  > /tmp/m4b_foundation_post_nodes.txt
comm -23 docs/test_spec/baselines/m4b_foundation_node_ids.txt \
  /tmp/m4b_foundation_post_nodes.txt > /tmp/m4b_foundation_missing_nodes.txt
test "$(wc -l < docs/test_spec/baselines/m4b_foundation_node_ids.txt)" -eq 99
test ! -s /tmp/m4b_foundation_missing_nodes.txt
```

Acceptance records `baseline_count=99`, `retained_count=99`, `missing_count=0`, plus SHA-256 of all
three lists. Any command error, duplicate baseline line, unsorted input or missing node is Fail.

Additional cases:

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `G01` | AST scan of all `src/**/*.py` and `tests/**/*.py`, plus pytest collection metadata | Foundation four-field constructor guard remains; no direct/aliased skip, xfail, `pytest.skip/xfail`, false constant assertion, deselection or marker omission affecting the 99 nodes or new M4B IDs |
| `G02` | run 99-node regression with strict markers and JUnit | failures=0, errors=0, skipped=0; no xfail/xpass; every baseline node appears once |
| `G03` | run complete `test_spec_M4B_foundation` focused implementation | all Foundation Test IDs Pass; replacement tests do not substitute for them |
| `G04` | dependency/diff inventory for candidate | all existing M1/M2/Foundation and shared config/SM/RM tests that import a changed symbol execute; report exact collected node list and zero skip |
| `G05` | M4A affected-boundary selection | run only existing portable nodes whose production dependency is changed or shared by M4B composition, unique-PID resource sampling, offline environment, privacy scan, process-group cleanup, TTS final-speech completion or Audio+LLM timeline; publish selector rationale and node list; do not rerun Pi M4A-only quality/latency acceptance |
| `G06` | compare candidate test inventory to pre-development exact SHA | deleted/renamed/weakened affected node or removed assertion is Fail unless an upstream approved authority explicitly replaces it; new nodes allowed |
| `G07` | Feed script Pass/Fail/Incomplete/Blocked cards to each PV result-state reducer | #2 script Pass becomes only `NeedsHumanReview`; #1/#3–#7 script Pass becomes only `NeedsDeveloperReview`; every non-Pass script status remains unsatisfied and cannot be overridden by a human record |
| `G08` | Supply Developer reviews with missing catalog rows, unequal expected/reviewed counts, stale result/evidence/catalog digest, wrong tuple/Test ID, inaccessible private locator, forbidden identity/signature fields, Pass with failed item, or Fail without an exact failed item | Every malformed/stale/incomplete review is rejected and never changes `NeedsDeveloperReview`; only a complete exact-result review produces Pass/Fail, without creating an approval/identity gate |
| `G09` | Aggregate complete/incomplete/mixed-attempt WAKE and RES case-card matrices, then replace one designated case after a Developer Pass | only all exact designated case scripts can create Test-ID `script_status=Pass,status=NeedsDeveloperReview`; case aggregate never emits final Pass; replacement invalidates the old Developer review and returns to `NeedsDeveloperReview` without rerunning unaffected cases |
| `G10` | Finalizer truth table over seven script statuses, three USER case verdicts, six Developer reviews, stale/wrong-tuple records and superseded attempts | `pv_status=Pass` occurs only for seven script Passes + three exact USER Passes + six exact Developer Passes on one tuple; every Needs/missing/Fail/Incomplete/Blocked/stale/partial combination is visible and cannot be filled by another Test ID, count or prior attempt |

## 5. Pi structural and human evidence plan

These Test IDs are defined now and remain Pending until the automatically bound tracked content, authenticated
target, implemented harness and Tester execution gate exist. Portable fake results cannot satisfy them. Initialize
one aggregate `PV` identity without launching a test:

```text
python3.13 scripts/run-m4b-pv.py init --pv-run-id <NEW_PV_RUN_ID> --public-root <NEW_EMPTY_PUBLIC_ROOT> --private-root <NEW_EMPTY_PRIVATE_ROOT> --binding-manifest <BINDING_JSON>
```

`init` fails unless both roots are newly empty and the binding manifest automatically attests the tracked content,
harness, measurement profile, target and artifacts. The seven Test IDs then run independently in any order. Each
exact command below requires a new sub-run ID, fresh setup and new empty per-ID partitions. Angle-bracket values are
execution inputs, not optional flags. No wrapper or retired launcher may replace these commands.

| Test ID | Authority and risk | Layer / timeout | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4B-PI-ATT-001` | Product §§2, 8–9, 11.2; stale input or wrong content/artifact/runtime/profile/target/root/fallback | script Pass → `NeedsDeveloperReview` → Developer Pass/Fail; 60 min | `<public_root>/<pv_run_id>/M4B-PI-ATT-001/<sub_run_id>/` |
| `M4B-PI-SEM-001` | Product §§2.2, 4, 6, 11.2; real answer meaning is unacceptable to USER | each case script Pass → `NeedsHumanReview` → USER Pass/Fail; 60 min Test-ID cap | `<public_root>/<pv_run_id>/M4B-PI-SEM-001/<sub_run_id>/` |
| `M4B-PI-CONV-001` | Product §§5–7, 11.2; genuine Conversation reuse/end/identity behavior diverges | script Pass → `NeedsDeveloperReview` → Developer Pass/Fail; 60 min | `<public_root>/<pv_run_id>/M4B-PI-CONV-001/<sub_run_id>/` |
| `M4B-PI-MEM-001` | Product §5.3, §§10–11; independent series is incomplete/unsafe or estimate is unauditable | script Pass → `NeedsDeveloperReview` → Developer Pass/Fail; 60 min | `<public_root>/<pv_run_id>/M4B-PI-MEM-001/<sub_run_id>/` |
| `M4B-PI-WAKE-001` | Product §9.2, §11.2; scripted preparation overlaps active ASR/listen | four case-script Passes → aggregate `NeedsDeveloperReview` → Developer Pass/Fail; 60 min | `<public_root>/<pv_run_id>/M4B-PI-WAKE-001/<sub_run_id>/` |
| `M4B-PI-TIME-001` | Product §10.2, §11.2; fresh fixed-audio timeline has mixed clocks or omitted nulls | script Pass → `NeedsDeveloperReview` → Developer Pass/Fail; 60 min | `<public_root>/<pv_run_id>/M4B-PI-TIME-001/<sub_run_id>/` |
| `M4B-PI-RES-001` | Product §§5.3, 7–11; independent network/resource/cleanup/privacy case fails | eight case-script Passes → aggregate `NeedsDeveloperReview` → Developer Pass/Fail; 60 min | `<public_root>/<pv_run_id>/M4B-PI-RES-001/<sub_run_id>/` |

Every command starts its own Engine/child and Product Session where applicable and tears them down before emitting
its result. It reads only the protected binding manifest and its own case fixtures. Controller, child, result card
and private manifest repeat the aggregate `pv_run_id`, unique `sub_run_id`, exact protected tuple and own partition
identity. No Test ID consumes another ID's transcript, turn, state, event, resource series, card or completion flag.
Bounded named barriers replace correctness sleeps and poll-until-lucky loops.

Script Pass is necessary but never sufficient for #1 or #3–#7. For #1/#3/#5–#7, Developer reads every public and
private numeric field, raw series row, trace row, terminal/output record and null reason; sampling only selected
rows or accepting an aggregate/count summary is forbidden. For #4, the script audits **every** raw point against
the schema, monotonic timestamp, unique-PID ownership, safety/identity rules and actual boundary coverage,
reports the audited count, exact extrema and anomaly/stop locators, and recomputes the formula on the complete
unchanged series. Developer inspects those auditable results, source evidence/units and digests, not every routine
sample by hand. An unexplained impossible, contradictory, truncated, constant/fabricated or otherwise unreasonable
value/output is Fail. Missing raw evidence, incomplete automatic audit or missing applicable Developer review is
Incomplete. Inspection ownership is:

| Test ID | Required Developer reasonableness review after script evaluation |
| :--- | :--- |
| `M4B-PI-ATT-001` | Every target fact, file identity, size, digest, prompt/schema/token count, profile field and READY output agrees with its source and describes the actual target; inspection includes the exact schema locator, 352-byte/final-LF/no-BOM evidence, digest `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`, decoded native keywords and separate Python semantic-validation proof |
| `M4B-PI-CONV-001` | Every input/output, token metric, revision, generation, turn ID, action, final close proof and cleanup row forms one plausible non-fabricated lifecycle; no unobserved context/replacement row is claimed |
| `M4B-PI-MEM-001` | Script checks every resource sample and unit, owner identity, health and boundary; Developer checks exact audited count/digest, actual boundaries and extrema, all anomalies/stops, formula inputs/intermediate drops/rounded thresholds/final estimates and native lifecycle plausibility |
| `M4B-PI-WAKE-001` | Every trace event, timestamp, barrier identity and component-activity output matches the commanded ordering without duplicated, missing or synthetic-looking rows |
| `M4B-PI-TIME-001` | Every clock mapping, timestamp, delta, audio/ASR/model/TTS output and null reason is internally consistent and physically plausible; no duration is silently treated as a product ceiling |
| `M4B-PI-RES-001` | Every network count, resource value, PID/PGID set, cleanup/recovery output, canary scan result and persisted-file observation is complete and plausible for its case |

After reviewing the applicable complete or focused audited inspection catalog, Developer records the per-Test-ID result through the
shared evidence command; this command records the review but does not perform or infer it:

```text
python3.13 scripts/run-m4b-pv.py record-developer-review --test-id <M4B-PI-ATT-001|M4B-PI-CONV-001|M4B-PI-MEM-001|M4B-PI-WAKE-001|M4B-PI-TIME-001|M4B-PI-RES-001> --pv-run-id <PV_RUN_ID> --binding-manifest <BINDING_JSON> --inspection-catalog <PRIVATE_INSPECTION_CATALOG_JSON> --reviewed-field-count <EXACT_EXPECTED_FIELD_COUNT> --reviewed-row-count <EXACT_EXPECTED_ROW_COUNT> --review-status <Pass|Fail> --failed-item <EXACT_CASE_OR_FIELD_LOCATOR_OR_NONE> --commentary <CONCISE_REASONABLENESS_NOTES>
```

The command resolves and binds the currently designated script result and private evidence manifest, verifies the
catalog/digests and exact expected-versus-reviewed counts, then writes the private Developer-review record from
§2.5. `--failed-item NONE` is valid only for Pass; Fail requires at least one exact case/field locator. Repeating
the command cannot overwrite a prior record; a corrected/rerun result uses a new attempt and new review record.

`M4B-PI-SEM-001` is the sole exception to Developer inspection ownership: its script evaluates native-path and
structural requirements, while USER inspects the three captured answers and supplies their semantic result.

### 5.1 Run bootstrap and automatic attestation — M4B-PI-ATT-001

Exact command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-ATT-001 --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `A01-NEW-ROOTS` | Start the ATT command against its new partitions and aggregate initialization record | aggregate roots were empty at initialization; ATT partitions are empty before this sub-run writes; earlier result, partial series, card, profile, threshold, transcript, status or digest is neither selected nor referenced |
| `A02-BOUND-TUPLE` | Attest before native import, then compare this sub-run's controller, child READY, result card and manifest | one tracked-content, harness, measurement-profile, target, artifact and partition tuple agrees field-for-field and by digest; untracked, dirty-but-unbound or otherwise unaccounted input is Fail |
| `A03 target-runtime` | Inspect the authenticated target and target-owned interpreter | Raspberry Pi model, Debian/OS/kernel, CPU/RAM, CPython `3.13.5`, ABI, SOABI and MULTIARCH exactly match; identity loss or mismatch is Fail |
| `A04 artifacts` | Inventory model, runtime closure, wheel/native/artifact lock, deployment files and notices | exact filenames, sizes and digests agree; deployment paths and licenses/notices are present; missing, extra, system-site, alternate-endpoint or fallback input is Fail |
| `A05 profile-ready` | Compare the profile, source response schema, artifact lock, deployed copy and READY field-by-field | profile ID and `profile_stage="measurement"`; both thresholds null; 57/9/66 prompt counts and three prompt hashes remain unchanged. Schema locator is exactly `requirements/m4b/semantic-output-v1.schema.json`; the deployed artifact is the exact 352-byte UTF-8 POC file with final LF/no BOM and SHA-256 `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`; profile, lock and READY repeat the same locator/digest. The decoded mapping has the exact object/member/type/`maxLength` content and no conditional semantic keywords. Tokenizer, sampling 0/1, threads 4, direct/reserve/context 32/128/1024, protocol 3 and offline fields agree; any regex/GBNF identity, embedded schema replacement, stale locator/digest, deployed-byte mismatch or unchecked digest constant fails before product credit; READY repeats the tuple with `pid == pgid`, no Conversation and no prewarm |
| `A06 obsolete-stage-negative` | Scan tracked content and exercise runner/schema negative inputs for the removed selection surface | no separate-PM bundle validator/export, `pm_complete`/`pr_complete`/`ph_complete` or equivalent flags, PM-to-PR purpose marker, release-rerun path, PH launch/validation path or temporary `run-pi-one-turn.sh`, `run-pi-two-turns.sh`, `run-pi-voice.sh` launcher can select, seed or validate `PV`; retained attestation/sampling/replacement/privacy/human/cleanup mechanisms remain reachable only through the canonical entry |

ATT verifies its own bound identity, offline profile flags and child `network_denial_installed` stage; it does
not claim a zero-network-attempt result or require a duplicate syscall trace. The independently isolated
`R01-OFFLINE` case in `M4B-PI-RES-001` captures actual network attempts from before native import through
exit and is the zero-external-attempt evidence. Neither case borrows the other's card, series or result.
ATT public cards contain identities, digests and counts only; raw paths and environment data remain private.
No ATT output gates another Test ID.

### 5.2 Three independent USER semantic cases — M4B-PI-SEM-001

Create one `M4B-PI-SEM-001` sub-run ID, then execute exactly these three case commands. Each command starts a
fresh Engine/child and fresh Conversation in new empty case-attempt partitions, records one real
listen→Reasoner→action answer and closes before the next case:

```text
python3.13 scripts/run-m4b-pv.py run-semantic-case --test-id M4B-PI-SEM-001 --case-id S01-IDENTITY --utterance '你是誰？' --pv-run-id <PV_RUN_ID> --sub-run-id <SEM_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --fresh-conversation
python3.13 scripts/run-m4b-pv.py run-semantic-case --test-id M4B-PI-SEM-001 --case-id S02-ENGLISH --utterance '想要英文進步應該怎麼做？' --pv-run-id <PV_RUN_ID> --sub-run-id <SEM_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --fresh-conversation
python3.13 scripts/run-m4b-pv.py run-semantic-case --test-id M4B-PI-SEM-001 --case-id S03-SEVEN-DAYS --utterance '為什麼一個星期有七天？' --pv-run-id <PV_RUN_ID> --sub-run-id <SEM_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --fresh-conversation
```

Each command is the required real-Pi prompt-in/normal-answer-out regression. Before a case can enter
`NeedsHumanReview`, script evidence must prove that the exact locked product prompt and schema were used, the
request traversed the genuine LiteRT-LM/Gemma path, `ResponseFormat.json(exact_response_schema)` was selected with
zero regex/GBNF/prefix-format call, and exactly one schema-valid non-empty `end=false` answer reached the normal
model-owned `speak + KEEP_NEXT` outcome. Empty output, `end=true`, R1/R2/E1, application fallback speech, retry,
replay, fabricated/pre-recorded model output or a fake runtime is `Fail`, not a completed semantic capture.

| Case | Prompt-in / required USER judgment over the captured model answer |
| :--- | :--- |
| `S01-IDENTITY` | `你是誰？` → identifies the assistant as 雪板 in a relevant, normal Traditional-Chinese answer |
| `S02-ENGLISH` | `想要英文進步應該怎麼做？` → gives relevant and practical English-learning advice rather than format fragments, punctuation-only output or unrelated text |
| `S03-SEVEN-DAYS` | `為什麼一個星期有七天？` → gives a coherent explanation of the seven-day week rather than merely echoing the prompt or emitting schema/control text |

Only these three cases require USER speech and judgment. Store the audio, exact product prompt identity, transcript,
response-format selection proof, constrained JSON/decode result and answer privately. Public evidence contains the
case ID, attempt ID, capture digests, script native-path/structural result and USER `Pass`/`Fail` verdict without
private content. Answer meaning is human-only: no keyword/personality heuristic, model-as-judge or automatic
semantic scorer may accept it. Recording failure or USER Fail reruns only that case, explicitly and with a new
case-attempt ID; it never reuses its failed Conversation and never causes another Test ID to run.

### 5.3 Genuine finite multi-turn and normal close — M4B-PI-CONV-001

Exact script command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-CONV-001 --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

This command creates its own Product Session and uses no semantic-case state, evidence, USER speech or human
judgment.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `C01-FIRST` | Script submits `請簡短介紹台灣。` | exact prompt and `ResponseFormat.json` schema reach one structurally successful real-model generation with normalized non-empty text and `end=false`; record revision, generation, turn and token metrics without scoring answer meaning; regex/GBNF/prefix formatting, R2, retry, replay, empty/normalizes-empty text or `end=true` cannot satisfy C01 |
| `C02-CONTINUE` | Script submits one labelled `0001 請再補充一點。` turn | same child/Conversation/generation as C01, increasing revision and genuine KV/history reuse; normalized non-empty `text`, `end=false` and `KEEP_NEXT`; record all turn/token/action rows without scoring meaning. A valid early `end=true` is the model's terminal, not a Core fault, but this attempt cannot credit the required continuing turn; no override or replay |
| `C03-CLOSE` | After C02's primary action, request normal application-owned Session close | matching three-part Conversation close proof and bounded owner/descendant cleanup complete; no third model end-intent decision, OPEN or replacement row is invented |

A directly affected portable PV-runner negative seam injects a schema-valid early `end=true` terminal at
`C02-CONTINUE` and proves the finite sub-run cannot become script/Developer `Pass`, does not replay or override
`END_SESSION`, and still performs cleanup. This seam checks disposition only; it supplies no real-Pi model or #3
`PV` credit. A controlled model-`end=true` outcome seam remains portable `M4B-OUTCOME-001` `O06`/`O07` on the
same final Pi bytes; it is not native real-model end-intent proof. Deterministic 1024-token admission,
pre-send rejection, application notice, sequential replacement,
explicit resubmission and following success are covered separately by portable `M4B-CONV-001` `C02`–`C05` on
the same final bytes on Pi with controlled admission snapshots. Such evidence must be labelled controlled,
not native-model natural context exhaustion.

### 5.4 Complete measurement series and estimates — M4B-PI-MEM-001

Exact script command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-MEM-001 --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

This sub-run creates its own Engine, Product Session, Conversation, sampler and raw series. Its scripted lifecycle
uses `請簡短介紹台灣。`, one labelled `0001 請再補充一點。` continuing turn, then normal
application-owned close. It neither reads `M4B-PI-CONV-001` evidence nor waits for a semantic/human result.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `M01-PROFILE` | Load the automatically attested profile through this harness and separately attempt normal AppConfig composition | profile identity agrees, `profile_stage="measurement"` and both thresholds are null; normal AppConfig rejects it; no role authorization, reviewer identity, signature, approval or freeze artifact is accepted |
| `M02-LIFECYCLE` | Execute the complete independent finite scripted lifecycle above | Engine, Conversation, both real model turns and their action/Audio boundaries, then normal application-owned close complete under this sub-run ID through exact `ResponseFormat.json` schema calls; both continuing results have non-empty normalized text and `end=false`, without semantic scoring; regex/GBNF/prefix formatting or premature model end cannot satisfy the planned lifecycle; no third model end-intent result is required; no other Test ID's event or status is referenced |
| `M03-SERIES` | Sample every actual lifecycle boundary and audit every saved point | complete unique-PID, `MemTotal`, `MemAvailable`, swap, temperature and throttling values exist at Engine-ready, Conversation-ready/preparation, before/after both generations, through action/Audio completion and after normal Session close; every timestamp/order/owner/health field is automatically checked and the audited count equals raw-series count; exact boundary/extrema and anomaly locators bind back to unchanged source rows; unexecuted replacement rows are not fabricated; duplicate/missing PID or sampler/identity loss is Fail |
| `M04-STOPS` | Evaluate the safety predicate before every new operation and record the target swap configuration/trajectory | enforce the 512 MiB floor and stop on OOM/kernel fault, throttling, temperature `>=80 C`, sampler/identity loss or cleanup failure; no operation begins after a stop condition; swap growth alone is not a stop or PASS/FAIL predicate |
| `M05-ESTIMATES` | Recompute from this sub-run's unchanged integer series | only a complete valid MEM sub-run derives both drops and estimates for the observed finite lifecycle; a stopped, failed, Blocked or Incomplete attempt emits explicit nulls with a stable reason; no unmeasured longer/replacement peak is claimed; record exact inputs, extrema source locators, outputs, audited count and digests without mutating a profile or launching another run |

For `M05-ESTIMATES`, recompute exactly:

```text
speak_drop_bytes = max(pre_speak MemAvailable - minimum through Audio completion)
generate_drop_bytes = max(pre_generate MemAvailable - minimum through primary action completion)
min_speak = ceil_mib(512 MiB + speak_drop_bytes)
min_generate = max(min_speak, ceil_mib(512 MiB + generate_drop_bytes))
```

`ceil_mib(x) = ((x + 1024**2 - 1) // 1024**2) * 1024**2`. Preserve the complete raw private series and
sanitized inputs, results and digests. The pair is `PV` evidence output only; it creates no release-profile
authority and exercises no threshold decision rows in this run. For an existing complete full-point catalog,
the exact raw-series point indices for each `pre_speak`/`pre_generate` and corresponding minimum are sufficient
extrema source locators; Developer may name them in the bound review commentary. A separate compact catalog or
new public card field is optional, not a prerequisite to review a valid complete series. Successful derivation
after validation of all `sample_count` saved points constitutes the automatic audited count; a sampled subset
or a count without successful full-series validation does not.

### 5.5 Controlled-wake core-wiring barrier exclusion — M4B-PI-WAKE-001

Execute the four cases separately. Each command owns a new case sub-run ID, attempt ID and empty evidence
partitions:

```text
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W01-OPEN-FIRST --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W02-ACK-FIRST --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W03-SLOW-OPEN --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W04-INTERRUPT-OPEN --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
```

`--production-wake-path` denotes the **core product wiring** under controlled wake stimuli, not physical wake
sensor or physical Display hardware verification. W01/W03 inject button-edge stimulus through `MockGPIO` into
actual `ButtonInputSource`; W02/W04 inject voice-wake stimulus through `MockWakeWordInputSource`. The Display
device may be `MockDisplay`. These are stimulus/observation endpoints only. Actual `ButtonInputSource`,
`StateManager`, Conversation control, `AlsaAudioInput`, `WhisperCppASR`, `DisplayArbiter` and `StatusBar` must run
with their product event/control connections. Tracing wrappers may observe but not replace their behavior.
Direct mutation of SM state, bypassing either wake-acknowledgement or matching Conversation-ready/join barrier,
or substituting a pure mock core is Fail and cannot produce a designated case card. USER speech, button action
and judgment are forbidden inputs. #5 provides **no Pass evidence** for a physical voice-wake sensor or physical
Display hardware.

| Case | Wake/order stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `W00-PRODUCTION-PATH` | Core product wiring check in every W01–W04 case, despite its retained assertion ID | result meaning is **core product wiring**: actual ButtonInputSource, StateManager, Conversation control, AlsaAudioInput, WhisperCppASR and DisplayArbiter/StatusBar are connected; W01–W03 complete both barriers before active path, whereas W04 interrupts pending OPEN with no completed barrier or active path; MockGPIO, MockWakeWordInputSource and optional MockDisplay are stimulus/observation endpoints, not hardware Pass claims; direct SM-state mutation, bypassed barrier or mock-only core is Fail |
| `W01-OPEN-FIRST` | `MockGPIO` → actual `ButtonInputSource`; OPEN becomes ready before wake acknowledgement | both barriers correlate to the same wake; no active listen path begins until both complete |
| `W02-ACK-FIRST` | `MockWakeWordInputSource` voice-wake stimulus; acknowledgement arrives before OPEN | both barriers correlate to the same wake; no active listen path begins until both complete |
| `W03-SLOW-OPEN` | `MockGPIO` → actual `ButtonInputSource` with bounded delayed OPEN | preparation may overlap only WAKE `準備中`; no premature active listen path occurs |
| `W04-INTERRUPT-OPEN` | `MockWakeWordInputSource` voice-wake stimulus interrupted while OPEN is pending | pending preparation closes without audio pull, active listen/ASR, perception worker or Reasoner admission |

For every row, before both wake acknowledgement and matching Conversation-ready/join barriers require zero
audio-frame pull, active listen/ASR, perception worker or Reasoner admission. Display is nonblocking and adds no
product Fact, state, turn or model content. Existing structured `production_path` fields (`state_manager`,
`button_source`, `voice_wake_source`, `audio_input`, `asr`, `conversation_control`), `display` fields
(`device_class`, `arbiter_class`, `status_owner_class`, `state_slot_only`) and bound barrier/activity trace are
sufficient W00 **core product wiring** result description when their actual values match the row above; no new
prose label or protected runner edit is required solely to rename `production_path`/W00. The card/capture must
not claim physical voice-wake sensor or physical Display Pass. Each case emits its own script outcome and requires Developer review of every trace
value/output before it can be designated; it can be rerun alone with new case identities and
partitions. Combine designated case cards without product execution:

```text
python3.13 scripts/run-m4b-pv.py aggregate-cases --test-id M4B-PI-WAKE-001 --pv-run-id <PV_RUN_ID> --public-partition <WAKE_AGGREGATE_PUBLIC_PARTITION> --private-partition <WAKE_AGGREGATE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON>
```

### 5.6 One-clock timeline — M4B-PI-TIME-001

Exact script command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-TIME-001 --audio-fixture tests/fixtures/m4b/pv/short-taiwan.wav --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

`T01-FIXED-AUDIO` uses only the bound fixed-audio fixture containing `請簡短介紹台灣。` and runs a fresh real
Audio→ASR→model→TTS→Audio path. Record the fixture filename, size and digest, require exact
`ResponseFormat.json` schema selection and one structurally successful terminal with non-empty normalized text
without semantic scoring, and accept no regex/GBNF/prefix formatting, R2/retry substitution, USER speech or
evidence from another Test ID. `T02-CLOCK-MAP` proves
controller/child monotonic mapping with bounded capture and no wall-clock substitution. `T03-NODE-ORDER` records:

```text
Conversation ready -> ASR final -> LLM send -> first safe text ->
LLM terminal -> TTS PCM ready -> Audio first positive write
```

Validate nondecreasing applicable nodes and cross-process clock mapping. Every missing/not-applicable
node is explicit null with a stable reason under `T04-NULL-REASON`. Report raw observations only: no latency
threshold, no PASS based on duration and no claim that Audio first positive write is audible onset. This Test ID
uses only its own fresh fixed-audio events and terminates its own child after capture.

### 5.7 Resource, cleanup and privacy — M4B-PI-RES-001

Execute the eight cases separately. Each command owns a new case sub-run ID, attempt ID, sampler/canaries where
applicable and empty evidence partitions:

```text
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R01-OFFLINE --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R02-HEALTH --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R03-PID --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R04-NORMAL-CLOSE --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R05-RECOVERY --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R06-FORCED-CLEANUP --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R07-SHUTDOWN --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R08-PRIVACY --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

Every command creates and tears down a fresh Engine/child/Product Session as applicable and uses no event, series,
card or completion flag from another RES case or Test ID.

| Case | Fresh scripted scope | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `R01-OFFLINE` | Capture attempts before native import through one structural turn and exit | zero non-loopback network, downloader, telemetry, DNS, alternate-endpoint or fallback attempt |
| `R02-HEALTH` | Run one complete generation/action/Audio/close lifecycle with resource sampling | zero OOM/kernel fault, throttle or temperature-stop violation; operation stops at `>=80 C` or the 512 MiB laboratory floor; report the measured swap trajectory without a zero-growth verdict or a swap-specific `Pass` assertion |
| `R03-PID` | Sample all controller/ASR/TTS/LLM owners through one lifecycle | every live owner appears exactly once by unique PID; duplicate/missing PID, identity loss, owner leak or sampler loss is Fail |
| `R04-NORMAL-CLOSE` | Complete one normal Conversation and Product Session close | matching three-part proof precedes bounded owner/descendant cleanup; zero orphan remains |
| `R05-RECOVERY` | Script one planned-recovery authorization and rebuild | primary action/rest and matching close proof precede the **actual** SM authorization; ledger binds close and authorization to the same session/generation, records successful `sm_authorized_ready`, old-PGID disappearance and new READY; one real-Reasoner following structural turn succeeds. Actual StateManager checks all three close-proof booleans and identity before authorization, and adapter checks proof equality with its saved close proof; on this fail-closed path, successful authorization/new READY is sufficient indirect R05 three-part proof evidence even if the capture does not duplicate the boolean fields. If either gate is mocked/bypassed or fails, this indirect proof is invalid and R05 cannot Pass |
| `R06-FORCED-CLEANUP` | Force the bound child PGID into its cleanup path | bounded forced-PGID owner/descendant exit and owner convergence occur; no rebuild or following-turn assertion belongs to this case |
| `R07-SHUTDOWN` | Keep a real resource sampler and native child live, then stop the real owners through their lifecycle | bounded owner/descendant and sampler exit; no owner leak or process retains the case partitions. This owner-lifecycle case alone is not full StateManager/product shutdown evidence |
| `R08-PRIVACY` | Inject private canaries, complete a structural turn/close/shutdown, then scan | logs, public evidence, temporary paths, argv/environment and persisted files contain zero raw canary or reversible-encoding hit; raw evidence remains access-controlled and public locators are opaque and digested |

Each case emits its own script outcome and public/private card pair, then requires Developer review of every
recorded value/output before designation. Failure reruns only that case with new case identities and empty
partitions; all other designated RES case cards remain unaffected while protected bytes are unchanged.
For R05, Developer inspects the exact close/authorization/new-READY ledger sequence, matching session/generation,
actual StateManager/adapter gate source and following native output. Missing copied proof booleans alone are not
Incomplete when that fail-closed gate evidence is present; a `close_proven` label or script assertion without
successful bound authorization/new READY is not a substitute.
For R07, `shutdown_invoked_with_sampler_live` is a live-at-owner-stop entry condition, not proof that the
StateManager/product shutdown path ran. Developer checks the actual owner-stop/child-exit/sampler-stop and
partition-holder evidence and does not describe this card as full product shutdown evidence.
For R08, Developer reviews every recorded numeric/structural field and the bound scan scope, zero-hit result,
canary digest, file modes and opaque public locators through sanitized Pi-local queries. The raw canary and
content-bearing private blobs must not be printed or exported for manual review: the script scans their actual
bytes and reversible encodings before emitting the sanitized result. A zero-hit count without the bound
scan scope and access-controlled source evidence is not a complete Developer review. If a native raw-text
digest differs from the captured answer digest, Developer computes a digest of
`validate_semantic(native_output).text` on the Pi without printing content and compares that **normalized**
digest to the captured answer; an unexplained mismatch is Fail, not an assumed normalization difference.
Public evidence contains only that case's assertion outcomes, counts, digests and opaque locators. Combine the
eight designated case cards without product execution:

```text
python3.13 scripts/run-m4b-pv.py aggregate-cases --test-id M4B-PI-RES-001 --pv-run-id <PV_RUN_ID> --public-partition <RES_AGGREGATE_PUBLIC_PARTITION> --private-partition <RES_AGGREGATE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON>
```

### 5.8 One disposition and later threshold adoption

After seven designated results exist, aggregate without launching product behavior:

```text
python3.13 scripts/run-m4b-pv.py finalize --pv-run-id <PV_RUN_ID> --public-root <PUBLIC_ROOT> --private-root <PRIVATE_ROOT> --binding-manifest <BINDING_JSON>
```

The final manifest exposes each Test ID, case and script assertion independently. It also exposes
`developer_review` for #1/#3–#7 and `user_result` for #2. It reports `pv_status=Pass` only when every Test ID's
script status is Pass, all six required Developer field-by-field reviews are Pass, and all three #2 USER case
results are Pass against the identical protected tuple. A script Pass without its applicable inspection result is
Incomplete. Aggregate counts, another Test ID or a superseded attempt cannot fill a missing result. Failure leaves
unrelated designated evidence intact; only the failed
single-command Test ID or failed SEM/WAKE/RES case reruns, with a fresh setup/attempt identity and no
protected-byte change. A valid MEM result
retains its independently derived estimates even while another Test ID awaits correction; an invalid MEM attempt
has null estimates and cannot be designated.

The byte-for-byte POC response-schema/content/profile correction creates a new protected tuple. Finalization
marks every regex/GBNF/`char+` tuple and the superseded minified `oneOf/const/minLength` / `642a94...` tuple
superseded, if present, and never selects either for the current aggregate result.
After implementation, development evidence must rerun the affected portable schema/decoder/outcome coverage,
new-tuple #1, the real-Pi normal-answer regression #2, complete #3, and the directly affected #4/#6 paths as
independent fresh sub-runs. Those runner-completion results are development evidence, not final acceptance.
Before commit or Verify handoff, final `PV` still executes all seven independent Test IDs against identical
new-tuple bytes; no old result, partial run or prior PASS can substitute.

Successful estimates remain evidence outputs. Later adoption is a new focused
`Design → Test Spec → Developer → Verify` delta, is not named `PR`, does not treat this `PV` as release-profile
authority and does not repeat the accepted semantic/human/context corpus by default. Its coverage is limited to
behavior directly affected by the adopted threshold values, followed by same-bytes Pi verification.

## 6. Requirement traceability

| Product §11.1 group | Portable Test IDs |
| :--- | :--- |
| 1. normalization/envelope/boundaries/no mutation | `M4B-NORM-001` |
| 2. prompt identity, exact constrained-JSON response-schema/profile identity, legal member order/whitespace, duplicate/extra/missing/type rejection, all four text/end combinations and spoken length | `M4B-PROMPT-001`, `M4B-SEM-001` |
| 3. UTF-8/JSON S2 extraction across both member orders, decoded-mapping terminal mode, prefix proof and explicit prohibition of regex/GBNF response formatting | `M4B-S2-001`, `M4B-WIRE-001` |
| 4. MEASURE/equation/ticket/disposal | `M4B-NORM-001`, `M4B-ADM-001`, `M4B-OUTCOME-001` |
| 5. fresh prefill tier | `M4B-PREFILL-001` |
| 6. canonical outcome rows, including final speak then rest, valid empty/true silent end and invalid empty/false R2 | `M4B-OUTCOME-001` |
| 7. Conversation continuity/replacement | `M4B-CONV-001` |
| 8. memory and planned recovery | `M4B-MEM-001`, `M4B-REC-001` |
| 9. complete child protocol including DISCARDING and next child | `M4B-WIRE-001` |
| 10. redaction, disposal lifetime and separate schemas | `M4B-PRIV-001` |
| 11. retained M1/M2/Foundation/M4A regression | `M4B-REG-001` |

| Product §11.2 evidence requirement | Pi/human Test IDs |
| :--- | :--- |
| artifact/runtime/ABI/profile/prompt/exact response-schema identity and digest, forbidden regex/GBNF path, offline/no fallback | `M4B-PI-ATT-001`, `M4B-PI-RES-001` |
| three independent real-Pi prompt-in/normal-answer-out cases with script native/schema-path proof and USER answer verdicts | `M4B-PI-SEM-001` |
| script-checked and Developer-reviewed real schema-constrained first and continuing turns, same-Conversation KV/history reuse and normal close/cleanup | `M4B-PI-CONV-001` |
| controlled model-`end=true` final speech/rest route on same final Pi bytes; not native end-intent proof | portable `M4B-OUTCOME-001` `O06`/`O07` |
| deterministic context admission, pre-send rejection, application notice, sequential replacement, resubmission and following success on same final Pi bytes with controlled admission snapshots | portable `M4B-CONV-001` `C02`–`C05`; not native natural-context credit |
| automatic attestation, independent complete measurement series and deterministic estimate evidence; no release rerun | `M4B-PI-ATT-001`, `M4B-PI-MEM-001` |
| four fresh scripted WAKE orderings with no USER trigger and no active ASR/listen overlap | `M4B-PI-WAKE-001` |
| fresh fixed-audio real Audio/ASR/model/TTS/Audio timeline, null reasons and no ceiling | `M4B-PI-TIME-001` |
| eight fresh script-checked and Developer-reviewed offline/health/PID/cleanup/recovery/shutdown/privacy cases | `M4B-PI-RES-001` |
| `NeedsHumanReview`/`NeedsDeveloperReview`, complete inspection-record binding, WAKE/RES case aggregation, stale-review invalidation and finalizer truth table | `M4B-REG-001` G07–G10 plus all seven Pi Test IDs |

## 7. Blocking findings

Focused byte-for-byte POC response-schema mapping disposition: **Revised — return to Designer for confirmation**.
The Tester-owned spec now binds the exact logical locator, 352 deployed bytes including final LF/no BOM, digest
`796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`, decoded mapping and
profile/lock/READY identity. It rejects an embedded substitute, unchecked digest constant, any deployed-byte or
locator mismatch, regex/GBNF path and the superseded minified `oneOf/const/minLength` schema. Native structural
constraints are explicitly separate from Python fail-closed `text/end`, normalization and spoken-length semantic
validation. Legal JSON lexical equivalence, duplicate-aware raw validation, direct decoded-mapping validation,
both S2 runtime surfaces and the real-Pi prompt-in/normal-answer-out regression remain mapped. Scripts evaluate
all seven Test IDs; USER judges #2 answer meaning. Developer inspects every number/output for #1/#3/#5–#7;
#4 retains complete raw evidence and automatic every-point audit, with focused Developer
boundary/extrema/anomaly/formula review rather than manual reading of every routine sample.

Product §11.2 now carries the same `NeedsHumanReview`/`NeedsDeveloperReview` authority. This Tester revision maps
the exact state transitions, complete inspection-record binding, WAKE/RES case aggregation, stale-review
invalidation and final seven-ID selection rule. Next owner is Designer to confirm synchronization and decide the
Developer gate transition; this Tester mapping does not itself modify Designer-owned status or product authority.

Developer source, executable tests, profile/lock and deployed artifacts remain unchanged by this Tester turn and
are explicitly nonconforming until Developer entry is reopened. Every regex/GBNF/`char+` protected tuple and all
earlier PM/PR/PH outputs are superseded and supply no current evidence. After implementation, affected portable
coverage and the named new-tuple Pi development reruns above are required; final `PV` still requires all seven
independently executed Test IDs on identical bytes before commit. No product test ran in this mapping turn, no
candidate SHA exists for the correction, and no development or `PV PASS` is claimed.
