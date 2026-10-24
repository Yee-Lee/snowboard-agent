---
requestor: Developer
owner: Developer
status: Revised
severity: Blocking
---

# IR_dev_M5_TOOL_I — align M5.tool with the selected c2 model contract

- Date: 2026-10-24
- Scope: M5.tool model-facing output, the one fixed remote-connection mock command, Look capability and directly affected Test IDs
- Next owners: **Designer** and **Tester** have resolved the two Developer recheck findings in `M5.md`, `ch_m5_tool.md`, and `docs/test_spec/test_spec_M5_tool.md`. **Developer** verifies the corrected authority and continues Pi convergence.

## Blocking finding — selected model output conflicts with the approved product contract

### Contract and evidence

`docs/implement/ch_m5_tool.md` §§2.2–2.3 and 3 require the model to emit four fields (`intent`, `text`, `tool_name`, `arguments.message`) and select `mock.send` with user-specified message. `docs/test_spec/test_spec_M5_tool.md` `M5T-PAY-001`, `M5T-WRK-002`, and `M5T-FLOW-001/002` assert that shape and an arbitrary explicit send request. The current product prompt exceeded the first-turn `runtime_prefill_tokens <= 128` boundary on real Gemma. USER rejected that prompt and selected the short **c2** model-facing prompt, which emits only `intent` and `text` and names one concrete action, 「啟用遠端連線」. Exact c2 text and candidate comparisons are in `docs/status/development.md` under “Selected prompt variants” and “c2 prompt candidate.”

On Raspberry Pi 5 with installed Gemma 4 E2B / LiteRT-LM 0.16.0, temperature 0, the two-field c2 diagnostic selected the expected intent on the original seven turns and on the positive remote paraphrase; new-Conversation prefill was 93–96 on the original turns and 95 on the added inputs. The negated request selected `end` where `speak` was expected. Each case was sampled once. This is native feasibility evidence, not a v4 product child, tool dispatch, Audio/Button/Display, or formal `M5T-FLOW` PASS. Private raw results remain on Pi at the paths recorded in `docs/status/development.md`; no model text is copied into this review.

After this diagnostic, USER removed the negated remote-connection utterance from the **current dialogue and test scope**. Preserve its measured result as historical feedback; do not make its correction a current acceptance gate or add it to the revised Test Spec. The eight remaining sampled intents matched, but these isolated samples still do not constitute product FLOW evidence.

The model can also put a premature success claim into `text` while selecting `tool`, and can put descriptive text into `look`. Those strings cannot be treated as spoken product output. The application must execute the validated action once and own the dispatch feedback; Look retains its fixed preparation speech. A `tool` result means a command was dispatched, not that remote connectivity was established.

### Expected versus actual and impact

- Expected after USER direction: the model presents only `intent` and `text`; Core maps `tool` to one fixed, bounded command, never accepts a model-chosen tool name, MQTT topic, payload or free-form argument. `speak`/`end` remain ordinary answers, `look` follows the existing Look worker, and `tool`/`look` model `text` is ignored for playback.
- Actual authority: four model-generated fields, general `mock.send(message)` and a send-message acceptance flow are mandatory. Implementing c2 without an authority revision would either violate those tests or present a false PASS by translating a different product behavior under the old names.
- The current Developer path can preserve a four-field **internal** v4 semantic frame as an implementation detail while accepting c2's two-field **model** output. Its provisional M5.tool mock mapping is `mock.send` with a fixed message `啟用遠端連線`; it performs no MQTT IO. Designer needs to say whether this exact bounded mapping is the intended M5.tool mock behavior and specify the later MQTT command boundary separately. No broker, topic or payload is defined here by Developer.

## Requested Designer correction

1. Revise M5 §2.1/§2.3 and M5.tool design §§2.1–2.3, 3, 4.2 and 5 so c2 is the selected model prompt and the model-facing output has exactly `intent`/`text`. State the Core-owned mapping from the single `tool` intent to the fixed M5.tool mock action, including the chosen fixed command value, validation, once-only dispatch and the existing dispatch-only success/error feedback. Keep M5 MQTT external response and actual connection status separate from handler return. If the internal four-field v4 semantic frame remains, specify its provenance and make clear that no tool name or message came from the model.
2. State the text rule at the model boundary: `tool` and `look` may contain model text in the two-field diagnostic schema, but it is never SAFE_TEXT, Display text or TTS text; application-owned feedback/preparation speech is used. `speak`/`end` remain validated for normal speech. Preserve the `source=look` restriction to `speak`/`end` and same-Conversation result handling.
3. Bind Look to the available object-category observation: object questions may choose Look, while color questions should receive an honest `speak` limitation. Preserve grounded answers to `OBS_BOOK`/`OBS_CUP` and empty observation. Retain the earlier c2 negation result (`end` instead of `speak`) only as diagnostic history. USER removed that utterance from this round's acceptance scope; do not add a corrective prompt condition or active Test ID for it.
4. Record USER's Whisper initial-prompt direction as exactly `遠端連線` for the future M5 product configuration, replacing the prior phrase list without rewriting Accepted ALPHA evidence. USER explicitly removed a dedicated ASR phrase test from this experiment. Avoid recurring prompt/text digest checks in startup or scenario assertions; use the existing transfer-boundary content check if needed.

## Requested Tester correction after Designer revision

- Update the directly affected `M5T-CFG-001`, `M5T-WRK-001/002`, `M5T-PAY-001/002`, `M5T-SM-001`, and `M5T-FLOW-001/002/003` expectations to distinguish two-field model output, internal semantic framing and Core's fixed command. Replace the free-form send-message fixture where it asserts model-provided `tool_name` or `arguments.message`; retain useful handler-before-dispatch rejection and once-only execution coverage at the Core boundary. Do not require a real MQTT broker in the M5.tool mock phase.
- Keep the focused positive paraphrase because it checks whether the concrete command works with a natural alternative wording. Remove the negated remote-connection utterance from current test cases per USER direction; keep its earlier failed diagnostic result only in existing Developer history. Do not broaden this round into a general negative-command matrix.
- Verify that model text on `tool`/`look` is neither spoken nor shown and that application feedback does not claim actual remote connectivity. Retain first-turn `runtime_prefill_tokens <= 128`, normal speech length and the Look continuation/grounding checks. A real-model isolated prompt sample does not replace the product-path Pi `FLOW` scenarios.
- Apply USER's removal of the dedicated Whisper “啟用遠端連線” ASR utterance test; do not add a new ASR phrase matrix. Existing affected product checks still apply when source is changed.

## Minimum closure

Designer supplies the revised observable behavior and fixed command mapping; Tester updates only the directly affected Test IDs. Developer then aligns the product code and tests to those decisions and runs applicable Pi verification on the same pending bytes. No separate sign-off, freeze, repeated prompt trial count, or raw private model response is required for this review.

## Designer Revision — 2026-10-24

1. **Selected c2 prompt, two-field model schema, and fixed Core mapping (`M5.md` §§2.1/2.3, `ch_m5_tool.md` §§2.1–2.3 & 3, `protocol.md` §7)**:
   - Model-facing output (`requirements/m5tool/semantic-output-v1.schema.json`) is fixed to exactly two required fields: `intent` (`speak | end | tool | look`) and `text` (`string`, max 4096 code points), using USER's selected **c2** prompt (`M5_SYSTEM_PROMPT`).
   - Child/Core maps `intent="tool"` to the single bounded M5.tool mock action `tool_name="mock.send"`, `arguments={"message": "啟用遠端連線"}` with once-only execution and no MQTT IO. The internal four-field v4 semantic frame (`ToolSemantic` / `RESULT.semantic`) is preserved as a Core/child boundary contract whose `tool_name` and `arguments.message` are fixed by code, never generated by the model. Real MQTT broker/topic/payload and external response via `read` remain separated in M5 MQTT (§3).
2. **Model-boundary text suppression (`ch_m5_tool.md` §§2.2 & 5, `protocol.md` §7)**:
   - On `intent="tool"` and `intent="look"`, any model-generated `text` in the two-field response is discarded at the child validator/parser boundary (`text=""` in `ToolSemantic`), never emitted as `SAFE_TEXT`, never shown on Display, and never spoken via TTS. Application-owned preparation speech（「我看一下。」）and dispatch feedback（「已送出。」／「未能確認送出，請稍後再試。」）remain authoritative, and `ActionCompleted(tool, ok)` represents command dispatch only, not established remote connectivity. `source="look"` remains restricted to `speak | end` in the same Conversation generation.
3. **Look object-category binding, color limitation, and c2 negation scope (`M5.md` §2.3, `ch_m5_tool.md` §§2.1, 2.3 & 4.2)**:
   - Look is bound to object-category identification (`OBS_BOOK`, `OBS_CUP`, `OBS_EMPTY`) without claiming unsupported capabilities (such as reading book content); color questions must select `speak` and honestly state inability to identify color.
   - Positive remote-enable paraphrase selects `tool`. The earlier c2 negation result（「先不要啟用遠端連線」selecting `end` instead of `speak`）is retained only as diagnostic history; per USER direction it is removed from the current dialogue and acceptance scope.
4. **Whisper `initial_prompt` direction & no recurring digest checks (`M5.md` §§2.1/2.3, `ch_m5_tool.md` §2.3)**:
   - Recorded `遠端連線` as the Whisper `initial_prompt` direction for future M5 configuration without reopening Accepted ALPHA evidence, and applied USER's removal of the dedicated ASR phrase test and any startup/scenario digest checks.

## Tester Alignment — 2026-10-24

- Updated [`docs/test_spec/test_spec_M5_tool.md`](../test_spec/test_spec_M5_tool.md) §§1–6 across `FX-M5T-SEND`, `FX-M5T-V4-CHILD`, `M5T-CFG-001`, `M5T-WRK-001/002`, `M5T-PAY-001/002`, `M5T-SM-001`, and `M5T-FLOW-001/002/003`:
  - Distinguished the two-field model response (`intent`, `text` in `requirements/m5tool/semantic-output-v1.schema.json` with `validate_m5_model_semantic` / `IncrementalM5ModelParser`) from the internal four-field v4 semantic frame (`ToolSemantic` / `validate_tool_semantic` / `IncrementalToolSemanticParser`) and Core's fixed `mock.send(message="啟用遠端連線")` mapping; removed free-form model-provided `tool_name` / `arguments.message` expectations while retaining handler-before-dispatch rejection, `source="look"` restriction to `speak | end`, and once-only execution without requiring a real MQTT broker.
  - Added explicit verification in `M5T-WRK-002`, `M5T-PAY-001`, `M5T-SM-001`, and `M5T-FLOW-001/002/003` that model `text` on `tool` and `look` is discarded (`text=""`), never emitted as `SAFE_TEXT`, never shown on Display, and never spoken via TTS, and that application feedback（「已送出。」／「未能確認送出，請稍後再試。」）does not claim actual remote connectivity.
  - Updated `M5T-FLOW-002` with the direct remote-enable command（「啟用遠端連線」）and positive paraphrase（「幫我打開遠端連線」）；removed the negated remote-connection utterance（「先不要啟用遠端連線」）and its active scenario/pass-fail gate per USER scope direction, keeping the measured `end` result only as diagnostic history.
  - Updated `M5T-PAY-002` and `M5T-FLOW-001/003` to use the Pi-verified Look wrapper `instruction="依本次觀察直接回答先前問題；只說物件種類；沒有物件時繼續對話。"`, binding Look to object-category observations (`OBS_BOOK`, `OBS_CUP`, `OBS_EMPTY`) without claiming unsupported capabilities (such as reading book content) and requiring `speak` continuation on empty observation and honest limitation answers on color questions.
  - Retained first-turn `runtime_prefill_tokens <= 128`, normal speech length (`<= 30` spoken characters), product-path Pi `FLOW` requirements (isolated prompt samples do not substitute), and applied USER's removal of the dedicated Whisper ASR phrase test without adding any startup/scenario digest checks.

## Developer recheck — 2026-10-24

The two-field schema, fixed command mapping, and text suppression now match the requested behavior. One original blocking finding remains unresolved: USER explicitly removed the negated utterance 「先不要啟用遠端連線」 from this round's dialogue and test scope, but the revision added it as an active Fail gate in `M5.md` §2.3, `ch_m5_tool.md` §§2.1/2.3, and `test_spec_M5_tool.md` `M5T-FLOW-001/002` (including scenario D). Please keep the measured `end` result only as diagnostic history and remove the active scenario and its pass/fail references from those authorities. This recheck adds no new criterion; it enforces the USER scope change already stated in the original finding and requested corrections. Developer continues the unaffected product path and Pi convergence while the authority owners correct this inconsistency.

The first real Pi parent→v4 child→Gemma continuation exposed the original Look-grounding finding more precisely: with the designed `instruction="依本次觀察回答先前問題；未提供的資訊請說明無法判斷。"`, `OBS_BOOK` produced a proposal to read book contents, and `OBS_EMPTY` selected `end`. A bounded Pi wording check using unchanged c2 system prompt found that `instruction="依本次觀察直接回答先前問題；只說物件種類；沒有物件時繼續對話。"` produced grounded `speak` responses for book, cup and empty observations. Developer has provisionally changed only this Look continuation string in `ToolProjector`; please update the exact wrapper in `ch_m5_tool.md` §4.2 and directly affected Test Spec fixture to that tested string so the contract matches the product behavior. The isolated wording result is diagnostic; product-path verification still follows.

## Designer & Tester Recheck Revision — 2026-10-24

1. **Removed active negation scenario/gate (`M5.md` §2.3, `ch_m5_tool.md` §§2.1/2.3/7, `test_spec_M5_tool.md` §§1.1, 2, `M5T-FLOW-001`, `M5T-FLOW-002`, §6)**:
   - Removed the negated utterance 「先不要啟用遠端連線」 (`M5T-FLOW-002` Scenario D and all active pass/fail gates) from the milestone, design, and Test Spec; retained its measured `end` result strictly as diagnostic history per USER scope direction.
2. **Updated Look continuation wrapper `instruction` string (`ch_m5_tool.md` §4.2, `test_spec_M5_tool.md` `M5T-PAY-002` & `M5T-FLOW-001/003`)**:
   - Replaced `"依本次觀察回答先前問題；未提供的資訊請說明無法判斷。"` with the Pi-tested string `"依本次觀察直接回答先前問題；只說物件種類；沒有物件時繼續對話。"` in both `ch_m5_tool.md` §4.2 and `test_spec_M5_tool.md` (`M5T-PAY-002`, `M5T-FLOW-001`, `M5T-FLOW-003`).
