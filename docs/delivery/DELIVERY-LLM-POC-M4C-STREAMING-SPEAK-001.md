# DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001

- Date: 2026-09-20
- From: LLM POC Team
- To: Core Designer, via PM
- Gate: `M4C-SS`
- Disposition: `B_RECOMMENDED`
- Evidence grade: `USER-DIRECTED ENGINEERING POC CLOSEOUT / NOT FORMAL 82-CASE EVIDENCE`
- Core baseline: `f87cfa50b9c9415430973076a59c6b1961228090`
- POC starting baseline: `5080abd84dafcbc0f8307a086fa8009a0b6a818b`
- Prospective tracked execution-surface SHA-256: `6ab4547e40afedabcbabe71061206abda11149a0208ae65bdf8168274631fdcd`
- Delivery source: the commit containing this document; exact pushed SHA is reported by the POC operator after push

## 1. Recommendation

Adopt true streaming-speak (`B`) and retain full-response (`A`) only as the failure fallback. The proved private
mapping is `B2-ONE-LOOKAHEAD-COALESCE`, using the existing Matcha TTS and Audio output interfaces. No JSON response
schema, cognition Fact, public TTS API, public Audio API, action, turn or correlation change is required.

Core should change the normal S2 release boundary from punctuation-or-24 normalized codepoints to
**punctuation-or-12 normalized codepoints**. Terminal constrained JSON remains authoritative; released text remains
ordered, non-revisable and an exact prefix of terminal normalized text. A punctuation-only tail may be coalesced
with the preceding queued fragment by B2; it is not dropped or rewritten.

This is the POC architecture recommendation requested by the User. It does not close `M4C-SS`, approve a product
API or provide M4C Test Spec acceptance; those decisions remain with Core Designer.

## 2. Scope decision and evidence semantics

The original Income defines 82 formal samples/subcases. During Pi-native development the User selected the
12-codepoint candidate after reviewing the boundary trade-off, then directed the team to close the POC without a
strict formal rerun and to verify delivery correctness only. Consequently:

- formal expected count remains 82 and formal executed count is **0**;
- no missing formal case is relabelled `PASS`;
- Pi observations below are `ENGINEERING / NON-FORMAL` evidence;
- `B_RECOMMENDED` is the User-reviewed POC design disposition, not a claim that the original section 8 formal
  matrix was completed; and
- a future Core/Test Spec qualification may reuse the delivered implementation but must define its own exact-SHA
  acceptance run.

## 3. Delivered implementation

The prototype adds a bounded incremental S2 extractor, configurable codepoint release boundary, blocking raw
LiteRT stream to async backpressure bridge, B1/B2 mapping runner, real child/TTS factory, USB acoustic capture and
onset analysis, private raw-stream/PCM retention with `0600` creation, and operator-gated engineering commands.

The safety invariants remain:

- at most one logical speak operation per turn;
- ordered exact-prefix fragments and terminal equality validation;
- queue bound of two fragments and 256 UTF-8 bytes;
- shared cancel/abort ownership with no post-cancel admission;
- terminal `LLMResponse` remains the only cognition Fact; and
- raw model text and microphone PCM remain outside Git.

Workstation verification after bringing the controlled Pi source diff back:

```text
.venv/bin/python -m unittest discover -s poc_llm/tests/m4c_ss -p 'test_*.py'
Ran 78 tests — OK
git diff --check — PASS
```

The Pi development checkout completed 76/76 tests before the final workstation-only detector wiring regression;
the workstation then completed 78/78 including both new onset-bound tests. No model, raw journal, PCM,
credential, endpoint, host identity, cache or generated artifact is included in this delivery.

## 4. Acoustic path and calibration

The physical measurement path was I2S VoiceHAT speaker playback plus an independent USB microphone capture. It
did not use the collinear I2S microphone, Listen, ASR or barge-in. USB capture was 48 kHz mono S16_LE with 10 ms
blocks. The dependency-free calibration measured 20.060403 ms combined clock/detector uncertainty, below the
50 ms ceiling. The final live run reported 21.677030 ms acoustic uncertainty.

The first acoustic implementation incorrectly admitted a pre-write click as onset in the initial 24/16/12
captures. Those observations are invalid and retained as a measurement defect. The detector was corrected to
reject onset before Audio write, regression-tested and rerun. Only corrected values appear below.

## 5. Incremental LLM observations

The real LiteRT raw stream produced usable pre-terminal S2 text for all three reviewed public cases. These early
runs used the then-frozen 24-codepoint boundary and measured text release, not acoustic onset:

| Case | Public input | First SAFE_TEXT | Native final | Lead before final | Fragments |
| --- | --- | ---: | ---: | ---: | ---: |
| L01-IDENTITY | `你是誰？` | 2.106 s | 3.278 s | 1.172 s | 2 |
| L02-EXPLAIN | `天空為什麼是藍色的？` | 3.168 s | 3.699 s | 0.531 s | 2 |
| L03-ADVICE | `我應該怎麼加強英語口說能力呢？` | 2.356 s | 4.336 s | 1.980 s | 3 |

The early L01/L03 stdout transcripts predated private journal retention, so their exact answer text cannot be
audited and is not reproduced here. Their timing/fragment observations support API feasibility only. L02 was
subsequently rerun with an append-only private raw journal and was used for boundary discovery.

## 6. Boundary and TTS observations

One retained L02 generation was projected through all four release boundaries without regenerating the answer:

| Boundary | First release | First PCM after release | Projected acoustic onset |
| ---: | ---: | ---: | ---: |
| 8 | 15.258 s | 202.5 ms | 15.653 s |
| **12** | **15.629 s** | **302.7 ms** | **15.949 s** |
| 16 | 15.908 s | 352.8 ms | 16.529 s |
| 24 | 16.577 s | 503.2 ms | 17.437 s |

The corrected full-response A replay reached acoustic onset at 17.969 s. The selected 12-codepoint B replay
therefore improved first audible sound by **2.019 s**. This is a replay comparison over the same retained
generation, not a formal paired live A/B sample.

For the selected boundary, S2 produced fragment lengths `12 / 12 / 1`. B2 submitted `12 / 13` codepoints to TTS
because the punctuation tail was available while the prior audio was active. Concatenation equalled terminal text;
there was no omitted, duplicated, reordered or rewritten character. The full replay measured a 250 ms
inter-fragment acoustic gap and 5,650.6 ms total acoustic duration.

## 7. True live end-to-end result

The final one-shot used the actual chain:

```text
LiteRT-LM raw generation -> incremental S2 (12) -> B2 -> Matcha TTS -> I2S speaker -> USB microphone
```

| Metric | Observation |
| --- | ---: |
| LLM send to first SAFE_TEXT | 5,903.530 ms |
| First SAFE_TEXT to acoustic onset | 1,427.087 ms |
| LLM send to first acoustic onset | **7,330.617 ms** |
| LLM send to native final | 7,600.576 ms |
| SAFE_TEXT fragment lengths | `12 / 12 / 1` |
| TTS request lengths | `12 / 13` |
| Terminal normalized length | 25 codepoints |
| PCM bytes | 1,333,440 |
| Acoustic uncertainty | 21.677030 ms |
| Source/backend/capture cleanup | idle / idle / stopped |

The acoustic onset was 269.958 ms before native final. That number is not the correct A-versus-B user benefit:
the sequential A path would only start TTS after native final. Using the same observed 1,427.087 ms first-fragment
startup gives an A onset projection of 9,027.663 ms and a B improvement of **1,697.046 ms**. This projection is
consistent with, but does not replace, the 2.019 s retained-generation acoustic replay comparison.

## 8. Private evidence and cleanup

The final live run retained a `0600` raw journal and `0600` USB capture under the operator-managed M4C-SS private
root, neutral run ID `L02-live-e2e-12-b2-001`:

| Item | Bytes | SHA-256 |
| --- | ---: | --- |
| Raw stream journal | 1,455 | `0ba4198d158f24fe4f50e08f00111ac40cb03fb402cbcef5916e5de8238352d1` |
| USB capture PCM | 1,333,440 | `988d1cf278d203b2a6dede99593dfe22cd9d6bf30ae366d083f6e2ac3612148b` |

The earlier L02 boundary journal is neutral run ID `L02-boundary-discovery-001`, 1,481 bytes, mode `0600`,
SHA-256 `97e85b8a189845e12c96719899c7d0973d8331c7b41fef1e8fee5b4b99c8da14`.

After the final run, no LiteRT, Matcha, M4C-SS, `arecord` or `aplay` process remained, and no process owned any
`/dev/snd` node. The Pi was left powered on and released for other teams.

## 9. Candidate disposition and Core action

`B2-ONE-LOOKAHEAD-COALESCE` is recommended because it preserves the existing public interfaces and terminal
contract while obtaining a material audible-onset improvement. The POC does not recommend changing the JSON
wire format. Core should:

1. adopt streaming-speak B2 as the M4C design direction;
2. review and freeze punctuation-or-12 normalized codepoints in place of 24;
3. retain terminal JSON validation and A as failure fallback; and
4. decide the product/Test Spec qualification depth needed beyond this User-directed POC closeout.

## 10. Limitations and unfinished external decisions

- The original 82-case formal matrix, five-pair L01-L04 A/B run, real negative injections, resource series and
  human quality matrix were not executed; this is the explicit User-approved closeout reduction.
- The Pi runs used a dirty development checkout rather than a clean pushed exact SHA. Delivery correctness was
  checked by controlled source return and workstation/Pi 76-test regression, not strict hardware rerun.
- L01/L03 exact early transcripts were not journalled. Only L02 has the complete raw-stream/acoustic chain.
- The live A value is projected; the retained-generation A/B acoustic comparison supplies the direct 2.019 s
  observation.
- Core Designer still owns `M4C-SS` closure, product boundary adoption and any subsequent Test Spec acceptance.

No further LLM POC experiment is requested. A new run is needed only if Core rejects the reduced evidence scope,
requests exact-SHA qualification, or selects a boundary other than 12.
