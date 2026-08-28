# ASSESSMENT-LLM-M3-GATE2A-ENTRY-AUDIT-001

- **Status**: `EXECUTABLE REMEDIATED IN WORKTREE / REVIEW REQUIRED / NOT EXECUTED`
- **Date**: 2026-08-28
- **Scope**: entry audit and executable remediation after Gate 1 closure
- **Publication state**: worktree only; not committed or pushed

## Conclusion

Gate 1 is complete and Core-closed. The audit found that the old `001` runner could not implement
the accepted cumulative scope. The worktree now contains a replacement `G2A-PI-LLM-002`
executable candidate that runs only P2/P3/P4/P5/P8 for Gemma and User/Core-waived Qwen. Gate 2A
remains `NOT_STARTED` until this worktree is reviewed, published as a clean exact SHA and executed
on the Pi.

## Blocking executable gaps

1. `poc_llm/harness/gate2a-pi-lock-v1.json` still identifies packet
   `G2A-PI-LLM-001`, not `G2A-PI-LLM-002`, and does not bind packet `002`.
2. The lock binds `p5-extreme-generation-001.json`; it does not bind the accepted
   `p5-continuous-timeout-002.json` fixture or a runner implementing its single outer timer and
   fixed `CONTINUE` disposition.
3. `run_gate2a_pi.py` still requires a `G1-PI-COMPAT-006` finalist receipt. It does not consume the
   Core-accepted Gate 1 cumulative evidence, the four P6.1/P7.1 receipts, or the Qwen defect waiver.
4. The runner still executes and scores P6/P7. Gate 2A must carry Gate 1 P1/P6.1/P7.1/P10A/P11/P12
   unchanged and execute only P2/P3/P4/P5/P8.
5. The old runner's mandatory decision requires P7 PASS and therefore cannot represent Qwen's
   immutable P7.1 FAIL plus User/Core-authorized Gate 2A eligibility waiver.
6. The bound adapter/config/installer surface predates the Gate 1 v7 authenticated receipt flow and
   the frozen Gemma 1024 / Qwen 512 capacities. A replacement must preserve those exact identities
   and must not restore implicit 4096 capacity.
7. The result schema does not yet express the accepted cumulative carry-forward, P6.1/P7.1 names,
   Qwen defect waiver, written workaround disposition, or affected-only invalidation semantics.
8. Existing Gate 2 definition tests pass, but they authenticate the old `001` lock/runner and only
   inspect selected wording in packet `002`; they do not prove packet `002` is executable.

## Required closure before Pi use

- create one `G2A-PI-LLM-002` runner, lock, cumulative entry schema and result schema;
- bind packet `002`, both frozen candidates/configs, Gate 1 closure ACK, four replacement receipt
  identities, runtime/adapter/protocol/catalog, P5 continuous fixture and P8 fixture;
- implement ancestor plus execution-surface carry-forward verification without routine model rehash;
- run only P2/P3/P4/P5/P8 and preserve every Gate 1 score unchanged;
- implement the Pi-only continuous P5 outer timer, correlated timeout, same-child health and required
  cleanup/rebuild without an early-success or adaptive-fixture path;
- represent Qwen as eligible-by-waiver while retaining P7.1 FAIL; require written User/Core
  workaround disposition before any Qwen provisional recommendation;
- add fail-closed workstation tests for all preceding rules and complete the required executable
  packet review/authorization before connecting to the Pi.

## 2026-08-28 remediation

All eight executable gaps above are addressed in the worktree:

- `run_gate2a_pi_v2.py` and `gate2a-pi-lock-v2.json` implement packet `002` and score only
  P2/P3/P4/P5/P8;
- a schema-validated `G1-M4B-CLOSURE-001` entry binds the Core closure ACK, Gate 1 execution SHA
  and surface, four replacement receipt hashes and immutable per-candidate carried scores;
- nested Gate 1 locks and shared artifacts are revalidated, while the prior model receipt is checked
  by filesystem identity without a routine model rehash;
- Gemma uses Engine capacity/chunk 1024/512 and Qwen 512/256; implicit 4096 is schema-invalid;
- the P5 adapter uses official asynchronous generation, repeated fixed chunks under one 15-second
  protocol timer, exactly-once native cancellation, same-child health and standard rebuild;
- P8 owns an independent resident Engine and stores only hashes, dispositions and bounded metrics;
- the result schema forces Qwen P7.1 to remain `FAIL` and forbids normal provisional eligibility;
- The complete Gate 2 definition suite passes 42/42 and the unchanged Gate 1 suite passes 136/136. These are
  workstation design results only and provide no Pi P credit.

Remaining before Pi execution: User/reviewer approval, one milestone commit producing the clean
execution SHA, confirmation of the two persisted Gate 1 artifact-receipt paths after boot, then one
candidate per clean reboot. No Gate 2A candidate observation has been consumed.

The formerly missing Gate 2B Audio source dependency is also now located: Audio tag `audio_m4` at
annotated tag `audio_m4` (tag-object SHA `24b2571a23dde2f77027242b61142b0c1a59924c`), accepted completion
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`, delivery `POC-audio-DEL-2026-001-R1`, corrected
delivery SHA `ca51bce9b4e205d9c9faf004d41c27169f108a3f`, and Core acceptance
`RESP-AUDIO-M4-GATE2B-001` at `be19b70b1dd91674e7ff981eb9d6b2dca9741f54`. Gate 2B is no
longer blocked on source identity, but its combined executable revision and Pi artifact staging
remain unfinished.

## Target state retained

The Pi was restored after Gate 1, then safely powered off. Persistent models and the wheel remain
under `/var/tmp`; `/tmp` staging must be recreated read-only after the next authorized boot. No
Gate 2A candidate observation has started or been consumed.
