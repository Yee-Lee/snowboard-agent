# M5.tool — 有限能力選擇、mock 派發與 Look 接續

Owner: Designer。產品決策來源：[M5](../milestones/M5.md)；正式開發 entry 見
[current](../status/current.md)。本設計已具體化；涉及 architecture 的新條文等待
[AR_impl_M5_TOOL_I](../reviews/AR_impl_M5_TOOL_I.md) 落入 authority 後交 Test Spec。
不把本文件當作已取得架構裁定或執行 PASS。

## 1. 價值、基礎與範圍

最小目標是真實 Gemma 能選擇說話、送訊或觀察，並在下一輪用 mock 觀察回答原問題。
保留已接受的 Audio、Gemma 4 E2B、LiteRT-LM 0.16.0、單一對話 Conversation 與
每產品 turn 最多一次推論。新增 profile `core-m5-tool-001`；M4B 文件仍描述已交付 profile，
不回寫歷史結果。M5.tool 不是另做 LLM runtime 選型。

Mock 邊界：`mock.send` 無網路副作用；Camera 回固定影像 fixture，Vision 回預設的觀察。
產品主流程仍走 ToolRegistry／Tool、Look worker、Reasoner、SM、Speak；不能另寫一條
測試專用對話流程。真實 LLM、TTS／Audio、button 與 selected Display 用於 Pi 整合／人工驗證。
MQTT broker／read 整合、真 YOLO 與 VLM 留後續階段。

## 2. 固定能力與語意輸出

### 2.1 M5.tool 的能力

| 語意 | 模型的責任 | Core 路由 |
| :--- | :--- | :--- |
| speak | 提供短回答 | speak + KEEP_NEXT + listen |
| end | 明確結束意圖及可選告別語 | 有文字則 speak + END_SESSION；空則 rest + END_SESSION |
| tool | 提供 registry 名稱及參數 | 驗證後 tool + KEEP_NEXT + listen，派發後固定 feedback |
| look | 要求本次觀察 | 固定 speak「我看一下。」+ KEEP_NEXT + look |

不讓模型輸出 Core session／turn／route、camera 資源名稱或任意 perception 清單。
Look 不是 ToolRegistry handler；兩者共用能力選擇，執行語意分開。

### 2.2 結構化模型輸出

採用固定 envelope，所有欄位必填，拒絕額外 key／重複 key／非有限數值：

```json
{"intent":"speak","text":"你好。","tool_name":"","arguments":{"message":""}}
```

- `intent` 為 `speak | end | tool | look`。
- `text`、`tool_name`、`arguments.message` 均為 string；arguments 恰有 message。
- speak：text 為非空短回答，tool_name／message 必須空。
- end：text 可空，其餘必須空。
- tool：text 必須空，tool_name 必須是已註冊且可用的 `mock.send`，message 為非空內容。
- look：text、tool_name、message 必須空，look capability 必須可用。
- speech 沿用 NFKC／空白 normalization 與最多 30 個 spoken characters；原始 text
  最多 4096 code points。tool_name 最多 64 code points；message normalize 後最多 40
  code points。這些是本 profile 的有界輸入／輸出限制，不是所有未來工具的通用 schema。

Runtime `ResponseFormat.json` 使用對應固定 object schema（intent enum、string 長度、
required、additionalProperties=false）。跨欄位互斥及 registry validator 仍由程式驗證。
Schema 資產路徑為 `requirements/m5tool/semantic-output-v1.schema.json`，由 Developer
與新 profile 一起加入；目前設計文件不宣稱該資產已存在或 LiteRT-LM 已驗證此 schema。
M5 新 domain 工具會修訂 schema／profile，不能為方便允許 arbitrary arguments。

### 2.3 模型 prompt

固定 core 指令與 schema 描述由此 profile 管理；附上實際可用能力及 registry 的唯讀
name／description／input_schema。禁止含 handler callable、credential 或私有識別資料。

核心文字：

> 你是「雪板」繁體中文語音助理。一般回答簡短、自然，最多30字。只輸出指定JSON。
> 一般對話用speak；使用者明確結束時用end。只有使用者明確要求送出訊息時才用tool，
> 工具名稱與參數必須符合提供的定義。工具派發不代表外部動作完成。
> 需要查看眼前畫面才能回答時用look；收到look觀察後，依結果回答先前問題，
> 不自動再次look，不執行tool。資料沒有提供的屬性不可猜測。
> 若輸入是source=listen的JSON，text是使用者原話，last_dispatch_status只表示上一輪
> 送訊派發成功或未確認成功；若輸入是source=look的JSON，facts是本次觀察。
> 目前測試的送訊與觀察使用mock，不能聲稱操作了真實外部設備或看到了真實相機畫面。

保留既有溫暖自然、稍帶幽默的人格設定。實際 prompt／schema 由 Developer 實作成一份
固定產品資產，不把 YAML 任意 suffix 或每輪 prompt 實驗放進產品。native 真實模型可能
需要修詞，修訂必須同步此設計並重驗受影響語意，不新增 approval round。
不自動計算 prompt／schema hash 或 token attestation；實際 token 數只用於 admission。

## 3. 工具派發與固定回饋

`mock.send` 描述：「模擬送出使用者指定訊息；只記錄一次派發，沒有外部設備副作用」。
arguments 恰為 `{"message": nonempty string}`；長度／normalization 同 §2.2。
Mock fixture 控制 success、已知 dispatch failure、可取消等待；這些控制不提供給模型。
驗證不執行 IO；派發只由既有 Tool worker 進行，不能由 Reasoner／SDK 呼叫 handler。

- `ActionCompleted(tool, ok)`：代表 mock 派發成功。
- `ActionCompleted(tool, error)`：沒有確認派發成功；不推定外部未執行，也不自動重送。
- handler return 不送給模型，也不作為外部 response。M5 真實外部訊息另經 read。

Composition root 對新 profile 注入固定 tool-feedback policy；SM 不自行讀取 LLM prompt
或猜測 profile。SessionContext.action_phase 增加 `tool_feedback`，in-flight phase 增加
`action_tool_feedback`；仍使用既有 ActionCompleted，不增加 Event Bus event 型別。

**SM 新增有限的 `tool_feedback` ACTION phase（待 Architect 採用）：**

1. Tool Fact＋task done join 後移除 primary record。
2. 對目前 profile 的 tool + KEEP_NEXT，建立唯一 Speak feedback record，使用不同 correlation；
   ok 說「已送出。」，error 說「未能確認送出，請稍後再試。」。
3. 留在 ACTION，不產生 ACTION→ACTION；feedback 不再次呼叫 Reasoner，不偽造 LLMResponse。
4. Feedback Fact＋task done join 後才進下一輪 listen。可翻譯 TTS failure 依既有 action error
   路徑繼續；worker crash／無法取消仍依既有 system error 處理，不繞過 recovery。
5. Interrupt／shutdown 取消當前 phase；舊 tool／feedback completion 不能啟動下一段。

這不是一般 action list；tool + END_SESSION、任意多個 action 組合不由本 profile 產生。
舊 profile 的既有 action 語意不變。Speak feedback 使用既有 TTS、Audio、Display 投影，
不由 Tool worker 直接操作 Audio。

固定回饋未經模型生成，因此下一個正常 listen 輸入帶一個 application-owned、
payload-free 的 `last_dispatch_status=ok|error` 提示，避免模型誤認派發狀態。SM 只保留
單一前輪結果及 generation，傳給 Reasoner 後在本次成功 generation 消費；Session 結束／
replacement 清除。它不是外部 response、跨 Session memory 或新增自動推論。
無前輪派發狀態時，listen 的 model-facing `text` 是 normalized utterance；有狀態時固定包裝：

```json
{"source":"listen","last_dispatch_status":"ok","text":"<normalized utterance>"}
```

`last_dispatch_status` 也可為 `error`。`text` 欄位以 JSON string encoding 放入原 utterance。
20 normalized code points 與 32 direct-user tokens 只檢查原 utterance；status wrapper
計入完整 native render／context admission，不占用使用者的字數與 token 限額。v4 MEASURE
帶 `user_text` 傳入原 utterance，詳見 [protocol §7](../protocol.md#7-m5tool-llm-protocol-v4)。

## 4. Look 投影與原問題接續

### 4.1 API 與 mock

沿用 Ch 2b `VisionAdapter.describe(image: bytes) -> VisionResult(text, extra)`，
Look worker 取得 Camera、執行 adapter 並回 PerceptionResult。M5.tool 的 mock 只替換
HAL／adapter，不跳過 worker、timeout、cancel 與 Event Bus。

Mock Vision 至少能返回兩份不同物件觀察、成功空偵測、可翻譯 error 及可取消 timeout。
具體 fixture 由 Tester 挑少量足以判別的內容；例如 book 與 cup 分別出現，模型不得把
第一份結果帶到第二次觀察。Mock 不宣稱 YOLO 已通過，也不強制真 Vision 使用同一 library。

### 4.2 model-facing input

新增 product projector，接受單一 listen 或單一 look；M5.tool 不啟用 read，也不接受混合
perception 組合。未知來源或不一致 session／turn 是 wiring error，不包成正常觀察。

Listen 保留現行使用者輸入 normalization 與 20 code points／32 direct-user tokens 限制。
Look facts 為非空、最多 512 normalized code points 的文字（可為 JSON 文字），不可套用
listen 的 20 字或 32-token 限制；Look 輪的 `user_tokens` 僅供觀測。
超長不截出可能失真的半份資料，回可用的輸入過長回饋並 listen。
所有來源仍做 exact native rendered-token admission；1024 context、128 output reserve
先沿用，並以 `current_kv_tokens + rendered_incremental_tokens + output_reserve_tokens
<= engine_context_tokens` 判斷。M4B 的首輪 `runtime_prefill_tokens <= 128` E1 常數
只適用 M4 profile，M5.tool 不繼承；實際無法容納最小合法 prompt／fixture 時回報
設計缺口，不假裝測過或默默加大。

Look 成功輸入格式固定為 application-owned wrapper，facts 以 JSON string encoding 保留邊界：

```json
{"source":"look","status":"ok","facts":"偵測到一本書。","instruction":"依本次觀察回答先前問題；未提供的資訊請說明無法判斷。"}
```

不加入虛構使用者語音、不重送全部 history。一次 Look 後只允許 speak／end；若模型仍選
look／tool，按已送出推論的 invalid semantic 路徑處理，不自動重試工具。

### 4.3 空結果、失敗與 Conversation 邊界

- 正常空偵測使用非空 facts「本次沒有辨識到支援的物件」，status=ok，交模型回答。
- 可翻譯 error／timeout：application-owned「這次無法取得影像，請再試一次。」→ listen，
  不啟動額外 LLM，不自動重新 Look。native crash／取消失敗依現有 ERROR／recovery。
- 選 Look 時 SM 在既有私有 SessionContext 記錄當時 generation；Look 結果只在該
  Session／generation 使用。正常路徑不 replacement。
- 結果產生前或 admission 時若必須 replacement，放棄本次結果及原問題接續，說明
  「這次無法接續原問題，請再說一次。」後按既有安全 replacement 流程回 listen。
  不把舊結果放進空白 Conversation。失去上下文按 error path 處理，不新增記憶系統。

### 4.4 錯誤分界與內部型別

| 發生位置 | 處理 |
| :--- | :--- |
| 推論前無可用 listen／Look 資料或來源長度超限 | application-owned retry speech＋KEEP_NEXT＋listen；不更動 Conversation |
| 需要 context replacement 且本輪是 Look | 放棄結果，說明無法接續，再用既有 replacement barrier 回 listen；不 replay |
| 推論已送出，semantic／tool 名稱／參數／當前輸入允許的意圖不合法 | 不派發；有 terminal 且 Engine 可用才走 R2 replacement，否則 E1；不靜默重送 |
| 已派發但 handler 回報已知失敗 | tool error→固定失敗 feedback→listen；不等待外部結果或自動重送 |
| 合作式 timeout／中斷 | 依各 worker 既有取消；取消後不 publish 正常成功，不啟動後續 phase |
| wiring、native crash 或不可證明已停止 | 現有 E1／recovery／fatal 分界，不能降格成「沒有看到」 |

新增 `ToolSemantic(intent, text, tool_name, arguments)` 作為 M5 profile 的 adapter semantic
值，`ToolSemanticGeneration(semantic, safe_fragments, metrics)` 回傳給 Reasoner；不把模型
object 直接當 Core LLMResponse。M4 SemanticGeneration 保留舊 profile 語意。
Reasoner 正規化後仍發布既有 LLMResponse。SM 的 generation／上一輪 dispatch status 透過
窄的 immutable cognition context 傳入，不讓 Reasoner 讀 SM 或 buffer 內部物件。

## 5. Streaming、SDK 與 child protocol

- 保持 automatic_tool_calling=false，工具執行永遠留 Core。
- M5.tool semantic parser 只有在已解析並鎖定 `intent=speak|end`，且目前已出現的
  `tool_name`／`arguments` 欄位沒有非空矛盾時，才能將解碼後的 `text` 作為 SAFE_TEXT。
  不等待尚未到達的空 tool 欄位；若 `text` 先於 `intent` 到達則先緩存，不假定 JSON key
  順序。`tool`／`look` 不輸出 SAFE_TEXT。Terminal 驗完整 schema 與已播片段一致性；
  後續欄位若違反互斥，報 `INVALID_SEMANTIC` 並依 R2 取消播音，不能派發工具。
- 若模型 terminal 不合法，依已交付的 R2／E1 規則取消播音及處理 Conversation，不執行工具；
  不為工具路徑關閉所有正常聊天 streaming。
- Tool 意圖等完整 terminal 驗證完成後才可派發。Look 的固定準備語在正常 ACTION 才播放。
- 新語意不能塞進 v3 的 text/end 假裝相容；`snowboard.llm/4` delta 見
  [protocol.md §7](../protocol.md#7-m5tool-llm-protocol-v4)。
  OPEN／measure／cancel／close 的生命週期沿用，新增 semantic terminal 與新 profile。
- 不新增影像 wire、vision backend 或額外 Conversation；那是 M6／VLM POC 的工作。

## 6. Composition 與可觀察性

M5.tool profile 固定 real LLM／Audio／TTS、mock Camera／Vision、mock.send registry、
look/tool enabled、external-message source/read disabled、voice wake disabled。Mock 由明確
開發 profile 選擇，不在真實 provider failure 後靜默 fallback mock。測試 UI／啟動說明標示模擬模式。

Factory 移除「所有 real model 都只能 listen-only」的單一 profile 假設，按 profile 驗證
composition；不改已交付 M4 baseline。新 profile 的 model/runtime identity 沿用，不重下載選型。
新 profile startup 與測試不計算／驗證 digest，不複製歷史 hash guard 作為新 gate。

公開 log 只記 intent、dispatch status、次數、sanitized code 與必要 timing，不記 prompt、
arguments、完整觀察或 private ID。語意與派發內容可在 private 判讀，公開結果只寫判定。
Display 用現有 SCN-ACTION-TOOL／SPEAK；不得顯示 raw arguments。觀察文字沿用既有
SCN-PERCEPTION 的產品顯示政策，與 log 隱私分開。

## 7. 實作路徑與交 Test Spec

先在 Pi 的真實 Gemma／LiteRT-LM 上驗固定 JSON schema 是否可產出四種合法語意，並量測
最小合法 prompt＋look facts 的 native rendered tokens。若 schema 不被 runtime 支援，或
在既定 context／output reserve 內無法容納，回 Designer 修正此 profile 的具體契約；
不能以手寫關鍵字分類、另一模型或默默縮減既有對話上下文宣稱 M5.tool 通過。

| 直接影響面 | 所需改動 |
| :--- | :--- |
| cognition/prompt_builder、semantic、reasoner | 新 profile prompt／schema、listen/look projector、intent validation、固定映射、last dispatch notice |
| cognition/litert_lm adapter／worker、llm_child_protocol | 新語意型別與 v4 terminal、stream parser、實值 ticket 綁定、profile composition |
| core State Manager | tool_feedback phase／record、取消、前輪 status 與 Look generation 檢查 |
| action/tool registry／mock | 沿用已驗證派發，增加單一無副作用 mock handler |
| Camera／Vision composition | 注入可控制 fixture，沿用 Look worker |
| config／安裝入口／Display | 新 profile 合法組合、模擬標示與 feedback 使用既有 Speak 投影 |

Developer 不重做已接受的 subsystem qualification，只對上列變動及其直接回歸驗證。
需求與語意 rubric 見 M5 §2.3；Tester 擁有 Test ID／命令／fixture 的正式規格，不由 Designer
冒寫執行 PASS。Architect delta 落定後即可進 Test Spec；不要求先完成 MQTT 或 VLM 研究。
