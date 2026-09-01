# AR1M2: Candidate Evaluation and Pipeline Selection

Status: `IN_PROGRESS — ENTRY GATES`

Entry date: 2026-09-01

Entry baseline: `asr_r1_m1`

## Entry fixture freeze

Before AR1M2A formal execution, close the four documented M1 coverage gaps:
intent taxonomy annotation, English named entities, controlled volume
conditions, and speech in noise. Collect or derive only the minimum authorized
prerecorded audio or annotations needed. Every row must carry its audited
identity, authorization, sensitivity, category, prior use, reference, checksum,
license, and controlled locator.

The User then reviews every proposed holdout row and the project freezes
disjoint development, adjustment, regression, and final-holdout manifests. The
final holdout remains untouched throughout AR1M2. This entry scheduling follows
`asr_r1/manifests/m1_fixture_schedule_revision.json`; it does not relax fixture
coverage or separation.

## Entry Pi 5 critical verification

Before formal scores or comparative results, check out one clean immutable
delivery SHA on a real Raspberry Pi 5 and repeat the critical exact-identity,
native/adapter smoke, partial/final, lifecycle, offline, resource,
temperature/throttling, cleanup, and bounded-shutdown cases for candidates that
remain eligible. Workstation M1 results cannot substitute for this aarch64,
CPU-only hardware evidence. A failed or unavailable row remains visible and is
reviewed before the formal packet is frozen.

## AR1M2A — Official Baseline Evaluation

Run eligible official pipelines and Whisper control on Pi 5 with frozen PCM,
real-time chunks, metrics, and repeats. Preserve native and wrapper results and
produce one comparative scorecard.

Workstation regression may validate harness behavior and reproduce functional
failures, but it cannot create formal scores, candidate rankings, or advance
credit. Every comparative result in AR1M2A is Pi 5 evidence from a frozen clean
SHA and packet.

## AR1M2B — Bounded Adjustment and Pipeline Selection

Use development data for one-variable probes of threads, official
chunk/context/lookahead, VAD/endpoint cooperation, and at most one justified
conversion. Do not train or fine-tune. Post-process is diagnostic only. Freeze
each AR1M3 pipeline; finalist count is not capped.

AR1M2B may use development and adjustment fixtures only. Regression data may
confirm that an accepted change did not break known behavior, but it provides
no holdout credit. No new fixture may be added after AR1M2A starts merely in
response to observed scores. A genuine coverage blocker stops the affected
formal run; preserve its evidence, revise the method before collection, obtain
review, and restart under a new frozen packet.

M2A and M2B share tag `asr_r1_m2` after reviewed completion.
