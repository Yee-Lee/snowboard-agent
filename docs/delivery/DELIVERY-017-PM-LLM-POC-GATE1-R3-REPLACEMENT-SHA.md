# DELIVERY-017-PM-LLM-POC-GATE1-R3-REPLACEMENT-SHA

- **Date**: 2026-08-26
- **From**: LLM POC Team (M4b)
- **To**: Core Designer
- **Status**: `DELIVERED / ACKNOWLEDGED BY CUMULATIVE-GATES-R3-ACK-001`
- **Replacement execution SHA**: `4dc76d1574daa7a9f7f56b98a8d65e00258fd46c`
- **Execution-surface SHA-256**: `568aa791ae572080ede637dc941887d8eee73553539e9ec3dc54a9979f92adc5`
- **Superseded execution SHA**: `b5690bbbef50ce37af356fd29b88ab920207c38e`
- **Continues boundary delivery**: `DELIVERY-015-PM-LLM-POC-CUMULATIVE-GATE-DESIGN`
- **Closes hold notice**: `DELIVERY-016-PM-LLM-POC-GATE1-R3-TARGET-UNIT-HOLD`

## Replacement scope

The R3 append-only candidate changes only the target-portable metadata-drift negative fixture and
its lock entry. The fixture now forces an observable timestamp change after an equal-size rewrite,
eliminating a same-tick false negative seen on Pi `/tmp`.

Runner, adapter, artifact authentication, schemas, configs, candidates, runtime/model identities,
thresholds, cumulative P allocation and result semantics are identical to the R2-approved design.
The User explicitly authorized this test-only fix without another reviewer round.

## Verification

- Workstation affected suite: 25/25 PASS.
- Physical Pi isolated pure suite: 14/14 PASS.
- Formal Gate 1 execution, swap change, network isolation and model load had not started when the
  target-unit finding was corrected.
- Branch `llm` contains immutable replacement SHA
  `4dc76d1574daa7a9f7f56b98a8d65e00258fd46c`.

## Core disposition requested

Please use this SHA and execution-surface digest in place of the R2 values when ACKing the cumulative
Gate design. The existing cumulative boundary remains unchanged. Per User authorization, Pi Gate 1
may execute while this ACK is pending; Gate 1 cannot close and P credit cannot finalize until the
replacement SHA and resulting evidence manifest are acknowledged.
