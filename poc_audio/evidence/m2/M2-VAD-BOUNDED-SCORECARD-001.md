# M2 VAD bounded scorecard

Status: `REVIEWED — WEBRTC FAIL / SILERO FAIL / EVIDENCE-BACKED NO-GO RECOMMENDED`

## Delivery contribution

This scorecard resolves the two authorized M2 VAD rows without tuning or a
candidate matrix. WebRTC 2.0.10 failed three frozen quality gates and activated
the conditional Silero 6.2.1 fallback. Silero then failed the frozen recall
gates. Both runs completed on Raspberry Pi 5 with exact artifacts, clean
worktrees, bounded execution, zero cleanup delta and no thermal throttling.

## Evidence binding

| Row | Exact POC SHA | Controlled result | Result SHA-256 |
| --- | --- | --- | --- |
| WebRTC 2.0.10 | `898e8053a9f773a04b01d9956653de9036459da2` | `~/.local/share/audio-poc/m2/vad-webrtc-898e805-001.json` | `9f01df8a59f46e852c77fab3a2d89efa31aed1ce437d56f094c02cb9b89004b8` |
| Silero 6.2.1 | `847e3c60adae158a79629d4fca2d24a3c4fec3bb` | `~/.local/share/audio-poc/m2/vad-silero-847e3c6-001.json` | `8fb3467c6d7c3097c1e824153c32b27fee6f5e97c44d7c833141c81028440c62` |

Both rows used the same 100 delivered Option A fixtures: 25 clear speech, 25
pause, 25 silence and 25 noise. The exact frozen label index SHA-256 was
`85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74`;
silence/noise duration was exactly ten minutes.

## Frozen gate results

| Gate | Required | WebRTC level 3 | Silero threshold 0.5 |
| --- | ---: | ---: | ---: |
| Speech-start recall | `>=95%` | `81.333333%` (`61/75`) — FAIL | `0%` (`0/75`) — FAIL |
| Speech-end recall | `>=90%` | `54.666667%` (`41/75`) — FAIL | `0%` (`0/75`) — FAIL |
| Start boundary absolute p95 | `<=300 ms` | `270 ms` — PASS | no matched boundary — FAIL |
| End boundary absolute p95 | `<=700 ms` | `160 ms` — PASS | no matched boundary — FAIL |
| Silence/noise false starts | `<=1/10 min` | `93/10 min` — FAIL | `0/10 min` — PASS |
| Cleanup | zero delta/residue | PASS | PASS |

WebRTC class results were: clear start/end recall `80%/40%`, pause
`82%/62%`, 26 silence events and 67 noise events. Silero produced no event in
any class. These outcomes are retained as candidate results, not averaged or
relabelled.

## Identity, runtime and observations

WebRTC used the exact 66,156-byte source SHA-256
`f1bed2fb25b63fb7b1a55d64090c993c9c9167b28485ae0bcdd81cf6ede96aea`.
Its Python 3.13/aarch64 wheel SHA-256 was
`16cab6c03362c5d0106e5b5f360c3b3c5a0a2a2a12eb0b3b2c1741443e805671`.
The upstream wrapper's undeclared `pkg_resources` import failed preflight; the
next immutable SHA used the same wheel's official `_webrtcvad` extension
directly. No engine code or profile changed after a result.

Silero used exact commit `7e30209a3e901f9842f81b225f3e93d8199902b1`
and original model SHA-256
`1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.
The unavailable historical POC-generated source representation was replaced,
before inference, by the official same-commit GitHub snapshot SHA-256
`266344c3ac556317012d55820265baea7806efe17d67fda8df83f9cb4a168716`.
The exact five-wheel closure is pinned in
[`m2_vad_silero_fallback.json`](../../manifests/m2_vad_silero_fallback.json).

| Observation | WebRTC | Silero |
| --- | ---: | ---: |
| Audio evaluated | `950 s` | `950 s` |
| Wall time / RTF | `0.555914 s / 0.000585173` | `7.008139 s / 0.007376988` |
| CPU, one-core basis | `35.475946%` | `99.982981%` |
| Peak RSS | `23.90625 MiB` | `80.78125 MiB` |
| Temperature | `35.30 -> 36.95 C` | `35.85 -> 37.50 C` |
| Throttle | `0x0 -> 0x0` | `0x0 -> 0x0` |

CPU, RTF and RSS are observations only under the reviewer-approved gate.
Before/after child, file descriptor and thread/task counters were identical for
both rows; independent post-run audio-owner checks returned no owner.

## Disposition

WebRTC is `FAIL / NOT FINALIST`. The frozen trigger correctly activated Silero.
Silero is `FAIL / NOT FINALIST`. Because both authorized rows failed and no
tuning, third row or retrospective gate change is authorized, the Technical
Lead recommends an evidence-backed VAD `NO-GO` for M2.

No additional VAD run is proposed. Reviewer/Designer must accept this no-go (or
issue a new written scope decision) before M2 closes. M3 must not start from
this scorecard alone.
