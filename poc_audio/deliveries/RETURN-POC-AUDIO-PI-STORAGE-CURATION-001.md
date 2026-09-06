# RETURN-POC-AUDIO-PI-STORAGE-CURATION-001

- Date: 2026-09-06
- From: Audio POC Team
- To: Core
- Request: `REQUEST-POC-AUDIO-PI-STORAGE-CURATION-001`
- Status: `PHASE 1 COMPLETE / REVIEW REQUIRED / NO PURGE PERFORMED`
- Audio base SHA: `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`
- Audio tag: `audio_m4`

## Returned files

- `poc_audio/evidence/PI-STORAGE-CURATION-EVIDENCE-INDEX-001.json`
- `poc_audio/manifests/pi_storage_cleanup_001.json`
- `poc_audio/deliveries/PI-STORAGE-CURATION-PHASE3-PLAN-001.md`
- `poc_audio/deliveries/RETURN-POC-AUDIO-PI-STORAGE-CURATION-001.md`
- `docs/pm_handoff/ACK-POC-AUDIO-PI-PHASE2-WORKSPACES-001.md`

The Core request remains an untracked intake file at
`docs/pm_handoff/REQUEST-POC-AUDIO-PI-STORAGE-CURATION-001.md`. No commit or push
was made, so the return SHA remains the requested base SHA. At the Phase 1
return point, the request plus the five returned paths were the exact six-file
uncommitted set. Phase 3 additions are listed separately in
`RETURN-POC-AUDIO-PI-STORAGE-PHASE3-001.md`.

## Inventory result

Every Pi path below is a logical locator. Its host-specific root mapping remains
outside Git in the controlled environment.

The four governed roots occupy 14,566,154,240 allocated bytes. Audio evidence is
now indexed separately from bulky run trees, including M2A/M2B CER and sentence
correctness, M3 final qualification, accepted M4 P9.1/combined/failure results,
and the required rejected histories.

Full SHA-256 inventory completed for the four named duplicate families:

| Object | Copies | Digest | Apparent bytes | Maximum duplicate bytes |
| --- | ---: | --- | ---: | ---: |
| Matcha `model-steps-3.onnx` | 44 | `524286bf6cf11be74329ae1c682ac69e34d6860c2ea9fd1290319d561540b16a` | 3,331,551,608 | 3,255,834,526 |
| whisper.cpp `ggml-base-q8_0.bin` | 9 | `c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9` | 735,917,265 | 654,148,680 |
| `vocos-16khz-univ.onnx` | 10 | `b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e` | 538,828,480 | 484,945,632 |
| ONNX Runtime 1.29.0 wheel | 6 | `d67673c5367727860922c5262d724472f1b5539fb7ccf4c81a638f9b71719803` | 124,897,578 | 104,081,315 |

Every copy in each group matched. The 4,499,010,153-byte maximum is a
same-content estimate, overlaps directory-level cleanup candidates, and cannot
be added to them.

## Worktree finding

The existing clean completion checkout is now the authoritative Phase 1
`audio` branch worktree:

- `PI_AUDIO_WORKSPACE/m4-completion-5694...`: branch `audio`, accepted
  `5694ead4...`, clean, tagged `audio_m4`;
- `PI_AUDIO_WORKSPACE/snowboard-agent`: detached historical `26f33a3...`;
- `PI_AUDIO_WORKSPACE/m3-session-20260824/checkouts/audio`: detached historical
  `655e80e...`.

Before reattachment, the stale local `audio` ref (`734369d...`) and stale
remote-tracking `origin/audio` (`26f33a3...`) were both verified as strict
ancestors of `5694ead4...`. Phase 1 fast-forwarded only the local ref and attached
the already-existing completion worktree; it did not create a worktree, fetch,
commit, push, rewrite a candidate, or move `audio_m4`. The Pi remote-tracking ref
remains stale. Core must still return the Phase 2 workspace receipt before Audio
uses the future canonical layout.

## Protected holds

- Current M4A product and its dependencies under
  `PI_M4A_RUNS/6c3ba95-20260829-dev01`.
- Accepted M4A tester cards/results under `6c3ba95-20260829-tester01`.
- `PI_M4A_PRODUCTS/m4a-runtime-closure-002`.
- Dirty telemetry worktree with four modified files and 112 additions.
- Accepted Audio SHA/tag, M3 r3, accepted M4 results, all failure/rejection
  evidence, and all only-copy reproduction inputs.
- Controlled/private audio, transcripts, hypotheses, logs, and User comments.
- Shared user caches, ambient site packages, Core `.venv`, and legacy archives
  whose ownership was not established.

No Audio-related model or worker process was running at inventory time. This is
an observation only and does not release any hold.

## Reclaim proposal

- Phase 1 authorized reclaim: `0` bytes.
- Conservative post-review path-level proposal: `2,214,473,728` allocated bytes,
  consisting only of enumerated build and per-run expansion directories whose
  result payloads remain outside the candidate path.
- Maximum equal-content duplicate estimate: `4,499,010,153` bytes. It overlaps
  the path-level proposal and depends on Core provisioning one verified object
  store, so the two values must not be summed.

No file was moved, staged for deletion, or permanently removed.

## Remaining work

1. Core reviews owner/category/expiry decisions and resolves the dirty telemetry
   worktree.
2. Core provisions Phase 2 canonical roots and returns their path, ownership,
   permission, and activation receipt.
3. The accepted M4A tester bundle must become self-contained before its dev01
   repo/config/controller/product dependencies can be retired.
4. Audio implements and tests the Phase 3 content-addressed artifact, runtime,
   and scratch separation against the returned roots.
5. Controlled/private retention periods require User direction.
6. Permanent purge requires a refreshed reference check, manifest review, and
   separate User approval.

## Validation performed

- Standard Git commands verified local and Pi SHA, tag, cleanliness, remotes,
  branches, ancestry, and worktree relationships; the accepted existing checkout
  was attached to the fast-forwarded local `audio` branch and remained clean.
- `du` recorded apparent and allocated bytes for governed roots and candidate
  paths.
- `sha256sum` verified all 69 files in the four duplicate families, including
  the sixth ONNX Runtime wheel in the SBD runtime closure.
- Accepted M4 result hashes were recomputed from their exact source paths.
- JSON syntax, manifest consistency, repository path existence, Git whitespace,
  and public-data safety checks passed on the returned uncommitted files.
