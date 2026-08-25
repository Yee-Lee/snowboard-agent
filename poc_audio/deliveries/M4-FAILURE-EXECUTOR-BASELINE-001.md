# M4-FAILURE-EXECUTOR-BASELINE-001

Status: `REJECTED EVIDENCE / FIX REQUIRED`

Candidate `8be3bc095b504b8eab1dfeb21b94173728b9656f` completed the fixed 12-case
failure/recovery catalog. Every injection reached its expected terminal state,
every recovery succeeded, the final process cleanup was zero, and live Pi checks
found no worker or device residue. However, `VAD error` and `VAD timeout` each
reported `threads +1`, so the validator correctly rejected a passing bundle.

The two threads were the formal controller's bounded asyncio executor workers:
the first was created by VAD startup and the second by concurrent run/abort.
They remained available to later cases and were shut down by `asyncio.run`, but
their lazy creation occurred after the first per-case baselines. The correction
prewarms the two controller executor threads required by run/abort concurrency
before any case snapshot. It also validates a provisional failure bundle before writing
raw evidence, so per-case residue produces a formal `FAIL` result instead of a
post-write validator exception. Rejected controlled evidence remains at
`controlled://audio-poc/m4/20260825/failure-8be3bc0`, SHA-256
`be5ab777d2608688d6b084a91ba6fdcc70dc1ba45005b229e79e930d3c2f5556`.
