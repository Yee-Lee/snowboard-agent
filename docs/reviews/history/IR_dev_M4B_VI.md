---
requestor: Developer
owner: Designer
status: Resolved
severity: Blocking
---

# IR_dev_M4B_VI — constrained grammar permits deterministic empty product output

- Date: 2026-09-13
- Scope: `M4B-PI-CONV-001` C01 and the locked M4B semantic grammar/profile identity
- Unaffected work: the independent PV harness, #1 attestation and all non-grammar Test-ID implementation may continue

## Blocking B1 — the locked grammar admits a product-invalid shortest path

### Contract basis

`test_spec_M4B.md` §5.3 requires C01 to submit `請簡短介紹台灣。` through the real
Reasoner/worker/model path and obtain a structurally successful first answer before continuing the
same-Conversation fill/replacement sequence. Product §11.2 maps the same requirement to
`M4B-PI-CONV-001` without human semantic scoring.

The current product semantic accepts an empty `text` only when `end=true`:
`validate_semantic()` rejects `{"text":"","end":false}`. The locked grammar and the equivalent
native runtime regex instead use `char*`, so constrained decoding admits an empty string for either
`end` value. The grammar therefore admits wire values that the immediately following mandatory
semantic validator rejects.

### Reproducible Pi evidence

On the bound Raspberry Pi 5 target, exact CPython 3.13.5, LiteRT-LM 0.16.0, locked Gemma 4 E2B
artifact, prompt, temperature `0.0`, profile and current protected-content digest
`6a6b89961ae6d5acbe0f8b5330ce816aab8d434bb2db4f36273b8d54069bdadf`:

1. Fresh PV sub-run `CONV-05` opened the real Audio output, ASR, TTS, Engine and Conversation.
   C01 decoded the exact structural value `{"text":"","end":false}`. The worker correctly
   returned `INVALID_SEMANTIC`; Reasoner correctly emitted the fixed R2 replacement response; the
   runner returned `M4B_PV_FIRST_TURN_FAILED` and proved cleanup. Earlier fresh native attempts
   `CONV-02` and `CONV-03` produced the same value.
2. A read-only native probe changed only the supplied response-format expression, not repository or
   target bytes. Allowing empty text only with `end=true` made the deterministic decoder select
   `{"text":"","end":true}`. That is semantic-valid but ends C01 and still cannot satisfy §5.3.
3. A second read-only probe changed `char*` to `char+` for all output text. The same model, prompt,
   sampling and C01 input then produced a non-empty `end=false` answer accepted by the existing
   semantic boundary. Pi swappiness/swap were restored after every bounded probe.

This is not a runner assertion defect: accepting the current R2 response as C01 success would erase
the required real successful generation and make the remaining same-Conversation test impossible.
Adding an automatic retry would also contradict the current invalid-semantic outcome matrix, which
requires R2 replacement rather than a hidden second GENERATE.

### Expected versus actual

- Expected: every grammar-admitted native result is eligible for the locked semantic validator;
  the fixed C01 input can produce one non-empty continuing result and enter the multi-turn sequence.
- Actual: `char*` exposes an empty shortest path. At temperature zero the bound model selects it
  reproducibly, so valid product handling necessarily replaces or ends the Conversation before #3.

### Impact

- `M4B-PI-CONV-001` cannot proceed beyond C01 on the selected production artifact.
- `M4B-PI-MEM-001` shares the same genuine lifecycle and cannot complete its measurement series.
- `M4B-PI-TIME-001` also requires one structurally successful real-model turn and is exposed to the
  same deterministic path.
- Developer cannot change the GBNF, runtime regex, semantic allowance or locked profile/artifact
  hashes without changing Designer-owned product identity and behavior.

## Requested Designer disposition

Preferred minimal correction: require at least one grammar character in every model-produced
`text` (`char+` in checked-in GBNF and the equivalent `+` native regex), while retaining the current
normalization, 30-spoken-character semantic limit, `end` boolean, failure handling, model/runtime,
sampling and Conversation lifecycle. This removes the grammar-only empty shortcut demonstrated by
the native probes.

Designer must explicitly decide whether removing model-produced empty `text` for `end=true` is the
intended product behavior. If silent model-directed session end must remain possible, Designer must
define another deterministic solution that both preserves that case and prevents a normal C01 input
from selecting either empty branch. A prompt-only preference is insufficient unless the bound
temperature-zero target proves the required behavior; a hidden retry is not authorized by this
request.

Directly affected identities and implementation surfaces after authorization are expected to be:

- `requirements/m4b/semantic.gbnf` and `src/sbd/cognition/semantic.py` grammar bytes/hash;
- `src/sbd/cognition/litert_lm/worker.py` equivalent native response-format regex;
- product profile/artifact-lock grammar identities and their deployed target copies;
- exact grammar/semantic/profile regressions plus native C01 and complete #3 rerun.

## Minimum closure and verification

1. Designer fixes whether all model-produced text is non-empty and aligns product §2.2/§11.2 and
   locked identity language without altering unrelated semantic or lifecycle behavior.
2. Tester maps the selected empty-text boundary and retains current invalid-wire fail-closed tests;
   no automatic retry or semantic scoring is introduced.
3. Portable tests prove checked-in GBNF, runtime regex, semantic validator and all profile/artifact
   hashes agree exactly; stale grammar/profile inputs fail closed.
4. On the bound Pi, the exact C01 path returns a non-empty structural continuing result, then the
   complete same-bytes `M4B-PI-CONV-001` reaches genuine context rejection, replacement,
   resubmission, following turn and cleanup.
5. Because this changes protected inputs, #1 and every affected prior development result are rerun
   on the final identical bytes before any commit.

## Designer response — Revised

Designer accepts Blocking B1. The grammar's zero-character path conflicts with the required native C01
continuation and permits a terminal value that the product immediately rejects. The selected minimal product
correction is:

- Every model-produced `text` must be non-empty after normalization for both `end=false` and `end=true`.
- Checked-in GBNF uses exact `string ::= "\"" char+ "\""`; the equivalent native regex uses `+`.
  The canonical revised four-line grammar SHA-256 is
  `fe97dc391364d875b9955cdfb283bd160b7845eae1e63734075da806973207b3`.
- Model-directed session end is therefore always non-empty final speech followed by rest. The former silent
  `{"text":"","end":true}` product outcome is removed. Application-owned silent end paths remain unchanged.
- A zero-character wire string or any string that normalizes to empty remains `INVALID_SEMANTIC` and takes the
  existing R2 cleanup/replacement path. No hidden GENERATE retry, prompt preference, replay or semantic scoring is
  added.
- Prompt bytes/counts/hashes, profile ID, model/runtime, sampling, 30-character rule, protocol and Conversation
  lifecycle remain unchanged. Grammar/profile/artifact-lock hashes change as protected inputs.

Product authority is revised in `ch_m4b_llm_production.md` §§2.2, 4.1, 6, 11.1 and 11.2. Focused Tester request
`TR_spec_M4B_IX` maps the affected grammar, semantic, S2, outcome, attestation and native C01 coverage before
Developer implements this grammar delta. Unaffected PV harness work may continue; grammar implementation directly
affects #1/#3/#4/#6. Because the grammar digest is part of the shared protected tuple, every designated result from
the old tuple is superseded if one exists, and final `PV` must run all seven Test IDs on the new identical tuple.
This response claims no implementation, acceptance or `PV PASS`.

## Designer resolution

Product authority and focused coverage now agree. `TR_spec_M4B_IX` resolved the exact grammar/semantic/S2/outcome,
identity, C01 and new-tuple evidence mappings without introducing retry or semantic scoring. Developer may apply
the authorized `char+` implementation and perform the required new-tuple Pi reruns. This closes the design blocker
only; it supplies no implementation result, final evidence or `PV PASS`.
