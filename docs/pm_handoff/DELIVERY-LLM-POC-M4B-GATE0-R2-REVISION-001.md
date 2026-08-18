# Core Team → LLM POC Team: M4b Gate 0 R2 Revision Request

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001`
- **Related handoff**: `PM-OUT-260817-015-llm-poc-contract-plan-review`
- **Related contract**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`, revision `2026-08-17`
- **Reviewed response**: `docs/response/RESP-PM-OUT-260817-015.md`
- **Reviewed POC branch / commit**: `llm` / `1d3444009a1edbf63e1b24a5e6977cbdb7203c80`
- **Rejected baseline retained**: `0cff62f942f2eec82fcc0b0f953a7cc4a2819e3a`
- **Status**: `REVISION REQUIRED — GATE 0 R2 NOT ACCEPTED`
- **Owner**: Core Team Designer
- **Architecture change**: `No`

## 1. Disposition

Core confirms that the revised commit is reviewable and that the four differences previously listed
against `0cff62f...` are materially corrected in the planning documents. The revision cannot yet
close or archive 015, because the newly supplied executable Gate 1 runner can issue a false `PASS`
without executing the mandatory Gate 1 candidate work claimed by the packet.

This Blocking finding could not have been executed during the prior review: the rejected
`0cff62f...` baseline did not contain this Gate 1 runner. It is therefore a direct review of the new
R2 implementation, not a new product preference or a retrospective threshold increase.

No Ubuntu candidate benchmark, Pi Gate 2A/2B execution or POC acceptance is recognized by this
delivery.

## 2. Exact-SHA intake verification

- The POC worktree was clean during review; local `HEAD` and `origin/llm` both resolved exactly to
  `1d3444009a1edbf63e1b24a5e6977cbdb7203c80`.
- `0cff62f942f2eec82fcc0b0f953a7cc4a2819e3a` is the parent/ancestor of the reviewed revision; the
  rejected baseline was not amended or replaced.
- The POC contract copy and Core contract both have SHA-256
  `d7d7adb84891803016b8656eb474f7a56bf39d5e416256192d003026c210585c`.
- All five artifacts listed by `poc_llm/harness/gate1-lock.json` matched their recorded SHA-256.
- Gate 1 validator self-test returned `PASS`, validator `1.0.0`, zero violations.
- Gate 2A and Gate 2B `--plan-only` commands returned `PLAN_VALID` with
  `execution_performed=false`; removing `--plan-only` returned `Blocked`, exit `3`.

These checks establish intake identity and safe Gate 2 planning behavior. They do not cure the Gate
1 false-positive described below.

## 3. `OUT-M4B-2026-007` — Blocking — Gate 1 runner can PASS without a candidate run

### Contract basis

The Core contract Gate 1 crosswalk requires the portable P1/P2/P3/P4/P5/P6/P8 subset plus P11,
both Ubuntu x86_64 and native aarch64 evidence, a frozen candidate/license/provenance packet and at
most two Core-ACKed proposed finalists. The POC packet additionally states that `PASS` requires both
platforms, hard eligibility/provenance, the exact 60-case matrix, performance evidence and cleanup
with no remaining child/process group.

### Reproduction and actual result

Core supplied a synthetic manifest named `CAND-NO-LLM-REPRO`. Its command did not start an LLM or
runtime; it directly asked the committed validator helper to print its own expected 20×3 JSON. The
reviewed command returned:

```text
{"candidate_id":"CAND-NO-LLM-REPRO",...,"result":"PASS",...}
runner_exit=0
```

The runner currently:

- checks only catalog/validator lock entries, not the complete locked candidate schema, runner and
  result schema;
- performs shallow manifest checks instead of validating `candidate.schema.json`;
- validates only the emitted P2/P3 normalized JSON;
- does not execute or verify portable P1/P4/P5/P6/P8/P11, exact runtime/model behavior or metrics;
- emits a report without the `cases` and `metrics` required by the committed result schema, and
  never validates that report against the schema;
- does not verify successful-run process-group/orphan cleanup;
- does not aggregate the two required platforms or execute the frozen ranking/max-two finalist
  decision.

### Expected result and impact

A command that merely reproduces expected fixture JSON, without running an eligible candidate and
the mandatory portable gates, must not receive Gate 1 `PASS`. The current runner can create evidence
that appears to authorize finalist selection and Gate 2A even though no LLM, lifecycle, performance,
provenance or cross-platform decision was tested.

### Required correction and minimum re-review conditions

POC may choose any equivalent implementation, but the committed Gate 1 packet must, as a complete
flow:

1. validate the candidate manifest with the locked candidate schema and validate every produced
   sanitized result with the locked result schema;
2. verify all locked runner/catalog/schema/validator identities and bind an immutable candidate,
   platform, command, artifact/config and run identity;
3. execute or fail-closed verify Gate 1 portable P1/P2/P3/P4/P5/P6/P8/P11 rather than deriving
   overall PASS only from the P2/P3 catalog;
4. preserve bounded timeout, exit proof and process-group cleanup for success and failure;
5. aggregate x86_64 and aarch64 results for the same frozen pairing and apply the committed
   deterministic ranking, selecting at most two proposed finalists or an evidence-backed no-go;
6. add regression evidence proving that a no-LLM command which prints validator-generated expected
   JSON is rejected and cannot create a Gate 1 PASS/finalist result.

Gate 1 does not need real candidate benchmark evidence to close this revision request; the required
outcome is a genuinely executable, fail-closed frozen packet and its self/negative tests.

## 4. Core decisions requested by R2

### P4 threshold disposition

The method and starting target remain frozen. A complete, valid P4 measurement below the starting
target must be returned as `Core threshold decision required` with raw samples, P50/P95 and the
candidate comparison. It is neither an automatic PASS nor an automatic no-go. Core/User will decide
only from that evidence; POC must not change the method or threshold after observing results.

### Pi 5 4GB mandatory floor

This delivery grants **no standing exception** to the 4GB mandatory floor. A valid 8GB result cannot
repair, substitute for or authorize a winner after a 4GB miss. If POC requests an exception, it must
return the original 4GB/8GB evidence as `Core threshold decision required` and await a separate
written Core/User contract decision; no exception is pre-approved here.

### Accepted Audio dependency

No Accepted Audio Gate 2B final handoff ID/full SHA/kit exists yet. Core commit
`790c0f86e12422542ef94cacd3c4dd850e346bca` carries a focused Audio Gate 1B candidate-scope ACK only;
it is not `POC Accepted`, a Gate 2A selection ACK or a Gate 2B final reference. LLM Gate 2B must stay
`Blocked` until Core supplies the later Accepted Audio final handoff identity and kit.

### Future ACKs

- Gate 1: Core ACKs at most two proposed finalists after complete both-platform evidence.
- Gate 2A: Core may ACK a provisional finalist only after the required Pi LLM-only evidence.
- Gate 2B: Core may ACK a final winner only after Accepted Audio intake, required 2A regression,
  P9 and P10B all satisfy the contract.

These future evidence-dependent ACKs are not required merely to close administrative handoff 015.
`OUT-M4B-2026-007` is the current closure blocker.

## 5. Required next return

LLM POC Team should revise only this finding and its direct impact surface, preserve the existing
`0cff62f...` and `1d3444...` history, then make one new reviewable commit and push it to `origin/llm`.
Return:

- response/authoritative packet path, branch and new full 40-character SHA;
- changed file list and finding mapping for `OUT-M4B-2026-007`;
- self-test and negative-test commands/results;
- confirmation that no Ubuntu benchmark, Pi run or candidate evidence was performed.

Core will re-review the new exact SHA only for this finding, its direct effects and newly introduced
regressions. Until that review passes, 015 remains open and Gate 0 R2 remains unaccepted.
