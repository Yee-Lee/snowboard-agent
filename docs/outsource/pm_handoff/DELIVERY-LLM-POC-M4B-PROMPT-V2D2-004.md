# DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004 — acceptable POC prompt baseline

- Date: 2026-09-08
- Status: `USER ACCEPTED / CORE REFERENCE / ENGINEERING NON-FORMAL`
- Runtime: Gemma 4 E2B, LiteRT-LM 0.16.0, Raspberry Pi 5 CPU/4
- Publication authority: User instruction on 2026-09-08

## Outcome

POC recommends V2D2 as an acceptable current prompt baseline. It retains constrained JSON and explicit
conversation-end control, includes a replaceable personality suffix, stays well below the 128-token
prefill tier, and produced usable streaming text before two seconds in every observed case. This is a
prompt exploration result, not a gate or formal benchmark. Future vision, tools and other perception
capabilities may revise the capability wording without replacing the Reasoner boundary.

## Exact prompt and semantics

Core prompt (57 model tokens):

```text
你是「雪板」繁體中文語音助理，只能聽與說，不能看或使用工具。只輸出含 text、end 的 JSON。一般回答的 text 不超過30字且 end=false；明確要求結束時 end=true。語氣：
```

Trusted personality (9 tokens): `溫暖自然，稍帶幽默。` Combined system prompt: 66 tokens.

`text` is speech content and `end` controls the state after speech. Non-empty `text` with `end=true`
now means speak the final message and then stop listening. Empty `text` with `end=false` remains invalid.
The prior MVA validator is unchanged; this semantic revision is isolated to the efficiency/Reasoner
proposal.

## Pi engineering observations

| Input | Answer | End | Runtime prefill | First safe text | Terminal |
| --- | --- | ---: | ---: | ---: | ---: |
| `你是誰？` | `我是雪板，很高興為您服務！` | false | 83 | 1.566 s | 2.835 s |
| `天空為什麼是藍色的？` | `因為太陽光穿過大氣，藍光會被散射出來，所以天空看起來是藍色的呢！` | false | 86 | 1.829 s | 3.981 s |
| `你看得到我嗎？` | `我聽得見您啦，您在想什麼呢？` | false | 85 | 1.735 s | 3.007 s |
| `你可以使用工具嗎？` | `我目前只能聽和說，不能看或用工具哦。` | false | 85 | 1.732 s | 3.001 s |
| `不用了，結束對話。` | `好的，沒問題！隨時都可以聊，下次見！` | true | 87 | 1.280 s | 3.070 s |
| `不要結束，說簡單一點。` | `沒問題啦，我會說得更簡單一點！` | false | 88 | 1.459 s | 3.004 s |

Fresh-Conversation runtime prefill was 81–88 tokens: 66 system tokens plus user and roughly 14
chat/runtime tokens. This is about 40 tokens below V2C's 125–131 range. The sky answer has 32 raw
codepoints and 29 spoken characters after three non-spoken punctuation marks are removed; the
30-character target therefore assumes the agreed pre-TTS punctuation/symbol normalization.

The no-punctuation confirmation pair ran three times with identical answers:

| Input | User tokens | Answer | Answer chars | First-safe median | Terminal median |
| --- | ---: | --- | ---: | ---: | ---: |
| `你好` | 1 | `嗨！您好呀，隨時可以問我任何事呢！` | 17 | 1.460 s | 3.457 s |
| `我應該怎麼加強英語口說能力呢` | 10 | `多聽多說，找對對話練習，會很有幫助喔！` | 19 | 1.736 s | 3.550 s |

The second turn used genuine Conversation/KV reuse and required 18 runtime-prefill tokens. All six
confirmation generations were structurally valid and stable. No Audio/TTS onset was measured, so
these first-safe-text observations do not establish the complete three-second audible-response claim.

## Acceptance and known limitation

The User accepts V2D2 at the present POC stage. Identity, basic answer, tool boundary, positive end,
negative end, length, personality and confirmation behavior are acceptable. The vision question was
not direct: `我聽得見您啦…` avoids explicitly saying it cannot see. The User treats this as nonblocking
because vision and other capabilities will require later prompt revision. Core should use V2D2 as a
compact, extensible reference rather than a permanent capability prompt.

All values are engineering observations from the Pi development workspace. Existing V1/V2A/V2B/V2C
records remain unchanged for comparison; the ambiguous prior `說明天空` confirmation is retained as
`INCONCLUSIVE / QUESTION_AMBIGUITY` rather than a V2C correctness failure.
