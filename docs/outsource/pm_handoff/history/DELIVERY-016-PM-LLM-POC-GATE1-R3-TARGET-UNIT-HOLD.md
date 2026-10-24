# DELIVERY-016-PM-LLM-POC-GATE1-R3-TARGET-UNIT-HOLD

- **Date**: 2026-08-26
- **From**: LLM POC Team (M4b)
- **To**: Core Designer
- **Status**: `HOLD PRIOR SHA / R3 TARGETED REVIEW PENDING`
- **Prior delivered SHA**: `b5690bbbef50ce37af356fd29b88ab920207c38e`
- **Prior execution surface**: `480adb939a6bfc359dfc2a10c9d478cece94df8fd24f8c48bb810d902e06d8d2`
- **Proposed R3 execution surface**: `568aa791ae572080ede637dc941887d8eee73553539e9ec3dc54a9979f92adc5`

## Hold notice

Please do not ACK or execute the prior SHA. Physical-Pi pre-execution pure validation found one
test-only nondeterminism before swap/network changes or model loading: an equal-size metadata-drift
fixture could complete within one `/tmp` timestamp tick and fail to create observable drift.

The proposed R3 change only makes that negative fixture deterministic with explicit `os.utime()` and
updates its lock hash. Runner, adapter, artifact-authentication behavior, schemas, configs, models,
runtime, thresholds and P mappings are unchanged. Workstation tests pass 25/25 and the isolated Pi
debug copy passes 14/14.

The POC will send one replacement exact SHA after targeted reviewer approval. This hold does not
request a Core decision and does not report a candidate or hardware result.
