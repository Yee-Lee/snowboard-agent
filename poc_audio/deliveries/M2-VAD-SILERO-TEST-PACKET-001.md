# M2-VAD-SILERO-TEST-PACKET-001

Status: `FROZEN / CONDITIONAL TRIGGER MET / NOT YET EXECUTED`

WebRTC result `vad-webrtc-898e805-001.json` triggered the authorized Silero
fallback by failing start recall, end recall, and silence/noise false-start
gates. WebRTC remains unchanged and is not rerun or tuned.

This packet fixes Silero 6.2.1 commit
`7e30209a3e901f9842f81b225f3e93d8199902b1`, the original exact ONNX model
SHA-256 `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`,
and the complete five-wheel Python 3.13/aarch64 runtime closure in
`poc_audio/manifests/m2_vad_silero_fallback.json`.

The historical POC-generated source archive is unavailable. Before inference,
this packet replaces only that archive representation with the official GitHub
snapshot of the same immutable commit, size 28,958,189 bytes and SHA-256
`266344c3ac556317012d55820265baea7806efe17d67fda8df83f9cb4a168716`.
The engine commit, model bytes, license, fixtures, scoring and candidate row do
not change.

## Frozen profile and gates

- 16 kHz mono S16_LE input; 512-sample/32 ms windows, final window zero-padded.
- Probability threshold `0.5`; recurrent state resets for every fixture.
- First positive window starts an event; 500 ms consecutive non-speech closes
  it at the last positive-window end; utterance padding remains 300/500 ms and
  is reported separately from scored boundaries.
- The exact WebRTC packet gates remain unchanged: start recall 95%, end recall
  90%, start/end boundary p95 300/700 ms, false starts at most 1/10 minutes,
  category breakdown and zero cleanup residue.
- CPU, RTF and RSS remain observations. One 100-fixture pass only; no tuning,
  threshold sweep, alternate windowing or rerun.

Run only on the clean Pi exact candidate SHA from the five controlled wheels,
official source snapshot and exact ONNX model. Preserve the controlled result
and submit `SILERO_PASS` as the M3 finalist recommendation or
`SILERO_FAIL_NO_GO` as the evidence-backed M2 VAD no-go recommendation.
