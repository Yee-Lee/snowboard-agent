---
requestor: Designer
owner: Tester
status: Resolved
---

# TR_spec_M4B_IX — map non-empty model-text grammar correction

- Date: 2026-09-13
- Scope: focused `IR_dev_M4B_VI` grammar/semantic boundary only
- Authority: `ch_m4b_llm_production.md` §§2.2, 4.1, 6, 11.1 and 11.2

## Request

Map the revised rule that every model-produced `text` is non-empty after normalization for both `end` values.
Preserve the existing `INVALID_SEMANTIC` R2 cleanup path; do not add retry, replay, prompt-only preference,
semantic scoring or changes to unrelated lifecycle behavior.

Required focused coverage:

1. `M4B-PROMPT-001` proves the checked-in GBNF uses `char+`, the native response-format regex uses `+`, and the
   canonical GBNF SHA-256 is `fe97dc391364d875b9955cdfb283bd160b7845eae1e63734075da806973207b3` across
   source constant, profile, artifact lock, READY and deployed copy. `char*`, stale digest or mismatched copy fails
   before credited product behavior.
2. `M4B-SEM-001` accepts non-empty normalized text with `end=false` and `end=true`; it rejects both empty wire text
   and non-empty wire strings that normalize to empty for either boolean. Retain the 30-spoken-character boundary
   and all invalid-wire fail-closed rows.
3. `M4B-S2-001` rejects empty/normalizes-empty terminal output without emitting fabricated safe text, and retains
   fragmented/coalesced UTF-8, escape, terminal and exact-prefix coverage for valid non-empty outputs.
4. `M4B-OUTCOME-001` removes silent model-directed end: non-empty/false remains KEEP, non-empty/true is final speak
   then rest, and empty-after-normalization for either boolean follows the existing proven R2 replacement path.
   Application-owned silent memory/interrupt endings remain unchanged.
5. `M4B-PI-ATT-001` attests the new exact grammar/profile/artifact identities and rejects the superseded grammar.
6. `M4B-PI-CONV-001` C01 on the real bound Pi requires a non-empty `end=false` result before the unchanged fill,
   exact context rejection, replacement, resubmission, following turn and cleanup sequence. No semantic scoring is
   introduced.
7. The grammar/content/profile digest change creates a new shared protected tuple. Mark every designated result
   from the old tuple superseded if one exists. During development, require new-tuple Pi reruns of #1, complete #3
   and the directly affected #4/#6 paths after implementation; final `PV` still requires all seven independently
   executed Test IDs on identical new-tuple bytes before commit.

## Minimum acceptance

- Test Spec and product authority agree on non-empty normalized model text for both `end` values.
- GBNF, native regex, validator and every locked grammar digest agree exactly; stale identities fail closed.
- The former empty/true acceptance and silent model-owned end are absent without weakening application-owned ends.
- Native C01 cannot Pass by R2, retry or an empty ending; it must obtain one non-empty continuing result.
- Mapping only: no product execution or `PV PASS` is claimed by this ticket.

## Tester response — Revised

Tester mapped the focused non-empty grammar correction in `docs/test_spec/test_spec_M4B.md`:

1. `M4B-PROMPT-001` now checks exact checked-in `char+` GBNF, native-regex `+` and grammar SHA-256
   `fe97dc391364d875b9955cdfb283bd160b7845eae1e63734075da806973207b3` across source, profile, artifact lock,
   deployed copy and READY. `char*`, the superseded digest and any copy mismatch fail before product credit.
2. `M4B-SEM-001` accepts only normalized non-empty text for both booleans; empty wire and non-empty wire text that
   normalizes empty are `INVALID_SEMANTIC`. Existing escape/control, 30-character and action-schema rows remain.
3. `M4B-S2-001` rejects empty/normalizes-empty terminal text for either boolean with zero `SAFE_TEXT`, successful
   RESULT or fabricated text, while retaining the valid fragmentation, UTF-8, escape, terminal and prefix cases.
4. `M4B-OUTCOME-001` maps empty-after-normalization for either boolean to the existing application-owned R2 notice,
   cleanup and replacement with no retry/replay. Non-empty false/true and application-owned silent endings remain.
5. `M4B-PI-ATT-001` checks the new grammar bytes/digest across every locked identity and rejects the superseded
   tuple before credit.
6. `M4B-PI-CONV-001` C01 now requires normalized non-empty `end=false` on the real bound path; R2, retry, replay,
   empty output or `end=true` cannot satisfy it. MEM and TIME independently require non-empty successful terminals
   on their directly affected paths without semantic scoring.
7. The grammar/content/profile digest creates a new protected tuple. Old-tuple designated results are marked
   superseded and cannot be selected. Development reruns new-tuple #1, complete #3 and directly affected #4/#6;
   final `PV` still runs all seven independent Test IDs on identical new-tuple bytes before commit.

Runner completion, old evidence and required new-tuple reruns are recorded separately in Test Spec §7. This is a
mapping-only revision: no product test was executed and no `PV PASS` is claimed. `git diff --check` passes.

## Designer confirmation — Resolved

Designer confirmed all seven requested mappings against the revised product authority. The Test Spec pins exact
`char+` GBNF/native regex and digest identity; rejects empty and normalizes-empty text for both `end` values;
preserves terminal/S2 fail-closed behavior; removes silent model-owned end; and keeps the existing R2 cleanup path
without retry, replay or semantic scoring. ATT, native C01, MEM/TIME direct impact and new-tuple invalidation are
explicit. Runner completion and old Pi evidence are not reported as current acceptance.

No Blocking finding remains. This resolves mapping only and opens the focused grammar implementation back to
Developer. Development must rerun new-tuple #1, complete #3 and direct #4/#6 paths; final `PV` still runs all seven
independent Test IDs on identical new-tuple bytes before commit. No product test or `PV PASS` is claimed here.
