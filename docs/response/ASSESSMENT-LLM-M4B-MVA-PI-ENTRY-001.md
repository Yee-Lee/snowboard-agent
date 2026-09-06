# ASSESSMENT-LLM-M4B-MVA-PI-ENTRY-001 — Pi executable-path proof

- Date: 2026-09-06
- Work / baseline / gate: M4B-MVA / M4B-MVA-001 / M4B-MVA-POC
- Authorized starting SHA: `ac25aa104adcadb3b6274ca6f9c3d4154b4004ee`
- Authorized starting surface: `f774c8d018445b91bef4fa3b59bcc4f288d6699deb1fd09a2cb9baf8f2ddc461`
- State: `PI EXECUTABLE PATH PROVED / REPLACEMENT SNAPSHOT REQUIRED`
- Hardware result: none published; replacement-source rehearsal is diagnostic, not exact-SHA formal evidence

## Authorization and delivery contribution

The User authorized direct Pi debugging, reboot-separated testing and the narrow artifact permission
remediation, while requiring network reachability to remain available between tests. Benchmark/profile
publication remains subject to User review. Work therefore used the clean canonical checkout only as the
accepted identity anchor and a separate private candidate worktree for source repair and rehearsal.

## Entry findings and repairs

Two append-only offline `prepare-install` attempts first established that the selected model and wheel
were unreadable by the `snowboard` service group, then that the runner assumed a flat
`runtime/litert_lm` tree while the accepted runtime uses a CPython virtual-environment
`site-packages/litert_lm` tree. The authorized permission repair changed only the two selected payloads'
group to `snowboard`; owner, mode `0440`, inode, size and content remained unchanged.

Direct Pi diagnosis then found and repaired four source-to-product integration defects:

1. Derive the authenticated runtime import root from the accepted native-library path, compare the
   wheel against that root, and give the child that exact `site-packages` path.
2. Preserve the content-addressed model `payload` as the authenticated object while presenting the
   exact same inode through a run-owned temporary `.litertlm` symlink required by LiteRT-LM.
3. Remove JSON Schema `if/then/else` from the native constrained-decoding schema because LiteRT-LM
   v0.16 LLGuidance rejects those keywords; retain the same `text/end` relation as fail-closed Python
   validation.
4. Align machine-evidence identity with the writer's required product-storage and cache-key fields,
   and allow ten seconds for native Engine shutdown before bounded TERM/KILL fallback.

The temporary model presentation is deleted with the run directory. No model, wheel, native binary,
raw prompt, raw answer or benchmark value is added to Git.

## Pi verification performed

The selected native Engine loaded successfully through the temporary `.litertlm` presentation. A real
public constrained generation returned the exact compact `text/end` shape. The full API proof then
confirmed selected-runtime import identity, tokenizer/census, two-turn Conversation reuse, cancellation,
fresh-session recovery and cleanup.

Regression execution on the Pi produced:

- MVA targeted suite: 66/66 passed.
- Pi storage-curation suite: 8/8 passed.
- Gate 2 suite: 84/84 passed with one documented platform skip.
- Repository Pi suite: 284 passed, one skipped and nine x86-only Gate 1 packet setup errors caused by
  the packet's deliberate `expected x86_64` guard on aarch64; a targeted traceback verified the guard.
- Private replacement-source rehearsal: all 23 machine case IDs completed once, including six distinct
  cold boots, ten same-boot replacement cases, three 20-session memory cycles and three recovery cases.
  The structural audit validated 1,847 schema-conforming samples, 60 complete memory sessions,
  checkpoint/final/summary binding and cleanup. Audit SHA-256:
  `2f225d6ff947043545537579d7ac7676b3683dac8ccefeaa247464bf77403361`.

Wi-Fi was restored after each required reboot and remained connected for the observable rehearsal.
Final postcheck found no MVA worker, zero swap use, no throttling and a clean accepted checkout. Raw
rehearsal records remain private outside Git.

## Disposition and remaining gate

The executable path and every automated MVA case type have now been exercised on the target Pi; there
is no known missing runtime API or unexercised machine-case branch. This does not convert the rehearsal
into formal hardware PASS/FAIL because it ran from an uncommitted private candidate with networking up.

The replacement source, tests, packet and non-recursive surface lock must pass local regression and be
committed as one clean SHA. That exact replacement SHA must then run the governed offline evidence round.
Afterward the User reviews benchmark values before any result/profile publication. Manual H01–H12 remain
a separate evaluator-owned WP04 activity. Audible-onset parity remains `null` with a missing reason unless
an accepted M4a Audio identity and common timebase are supplied; it is not required for the LLM-only
machine runner.
