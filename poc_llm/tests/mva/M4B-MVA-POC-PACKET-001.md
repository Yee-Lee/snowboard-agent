# M4B-MVA-POC-PACKET-001 — execution snapshot draft

Status：`WORKSTATION DESIGN / NOT COMMITTED / PI NOT AUTHORIZED`

- Work / baseline / gate：`M4B-MVA` / `M4B-MVA-001` / `M4B-MVA-POC`
- Income SHA-256：`5afb24e8ec7ad67853745ec290672c6b48a174819928936609556fefd184a2c2`
- POC starting SHA：`b5ce101d1f75889bfcc1bf6f38ed563f59c2d9a1`
- Frozen execution SHA：`PENDING USER COMMIT/PUSH AUTHORIZATION`
- Pi run IDs：`PENDING SNAPSHOT FREEZE`

## Frozen method inherited from the delivered request

The execution snapshot will bind the MVA profile, exact prompt/template bytes, semantic and wire
schemas, public catalog, runner, result schemas, ordered repetitions and scope exclusions in a
non-recursive surface manifest. The baseline uses one Conversation per product session, normal
two-turn reuse, compact `text/end`, and no disposable pre-warm. The only A/B variable is public
disposable pre-warm `none/once`; its Conversation is closed before opening the product session.

Cold order is exactly `N1/O1/N2/O2/N3/O3`; replacement order is exactly
`N1/O1/N2/O2/N3/O3/N4/O4/N5/O5`. Timing input is the public two-turn sequence
`天空為什麼是藍色的？` then `再簡單一點。`; pre-warm input is `請用一句話打招呼。`.
Samples are descriptive and report each value plus median/range, never a small-sample P95 claim.

Memory uses three fresh-child cycles of 20 complete two-turn sessions. Sessions 11–20 are the only
steady analysis window. Each cycle reports owner PSS and system-used raw values, OLS slope,
sessions 11–15 and 16–20 medians, and late-minus-early delta. Controlled recovery is three separate
`capacity_test` requests from READY_NO_SESSION; it is not manufactured memory pressure and does not
alter the natural soak.

## Pre-execution gates

1. Workstation contract tests PASS and exact tokenizer census proves every public input is within
   the 32-token new-user admission before inference.
2. Selected LiteRT-LM 0.16.0 runtime API proof covers render, tokenize, token_count, constrained
   response, same-Conversation reuse, close and cancel. Any unknown semantic is `Blocked`, not guessed.
3. Surface lock and result schemas are committed at one clean full SHA and pushed for Pi checkout.
4. User approves that exact SHA, Pi power/access, six reboots, bounded commands, raw path and cleanup.
5. Accepted Audio identity/onset method is either verified or the snapshot freezes
   `scope=llm_subsystem` with audible latency `null`.
6. Manual H01–H12 operator and private presentation path are assigned after prompt/schema freeze.

## Operational bounds

- Startup：120 seconds each.
- Generation：30 seconds each.
- Per mode：1800 seconds.
- Memory cycle：7200 seconds.
- Stop new work when MemAvailable is below 512 MiB, swap grows, OOM/kernel fault occurs,
  `get_throttled != 0x0`, temperature is at least 80°C, identity/sampler evidence fails, or cleanup
  cannot be proved. Preserve the same-schema sample and perform bounded cleanup.

## Publication boundary

No benchmark result or profile recommendation is published before User review. Machine outcomes,
target misses, invalid/missing samples and cleanup failures remain immutable. Core Designer alone
adopts the final product profile and releases `M4B-MVA-POC`; this packet cannot claim Gate 3 PASS.
