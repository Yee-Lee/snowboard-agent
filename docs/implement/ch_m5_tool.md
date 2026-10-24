# M5.tool — 有限能力選擇、mock 派發與 Look 接續

Owner: Designer。產品決策來源：[M5](../milestones/M5.md)；正式開發 entry 見
[current](../status/current.md)。架構中的有限語意與 tool feedback 契約已落定；
本設計交 Tester 建立 M5.tool Test Spec，不把文件完成當作執行 PASS。

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

| 語意 | 模型的責任（兩欄 JSON：`intent`, `text`） | Core 映射與路由 |
| :--- | :--- | :--- |
| speak | 提供完整短回答（`text` 為正規化後非空且 `<= 30` spoken characters） | speak + KEEP_NEXT + listen |
| end | 明確結束意圖及可選告別語（`text` 可空） | 有文字則 speak + END_SESSION；空則 rest + END_SESSION |
| tool | 僅選擇 `intent="tool"`（`text` 由應用程式忽略，不作為命令參數或播音） | child/Core 固定映射為 `mock.send(message="啟用遠端連線")` → 驗證後 tool + KEEP_NEXT + listen，派發後固定應用程式 feedback |
| look | 僅針對眼前物件種類辨識要求選擇 `intent="look"`（`text` 由應用程式忽略） | 忽略模型 `text`，固定 speak「我看一下。」+ KEEP_NEXT + look |

不讓模型輸出 Core session／turn／route、工具名稱、MQTT topic、payload、自由參數、
camera 資源名稱或任意 perception 清單。Look 不是 ToolRegistry handler；兩者共用能力選擇，
執行語意分開。

本設計以三個平行名稱描述產品路徑；名稱不是模型輸出欄位，模型仍依上表輸出
`speak | end | tool | look`：

- **answering（基本回答路徑）**：模型輸出 `speak` 或 `end`，其 `text` 經正規化與長度驗證後作為回答或告別語，Core 依既有回答／結束 route 執行。詢問顏色等超出目前物件種類視覺能力的問題，亦走 `speak` 誠實說明無法辨識。
- **dispatching（命令派發路徑）**：使用者明確要求啟用遠端連線（含正向換句話說，如「幫我打開遠端連線」）時，模型輸出 `intent="tool"`；child/Core 忽略模型 `text`，將單一 `tool` 意圖固定映射為 M5.tool 的有界動作 `mock.send` 與固定參數 `{"message": "啟用遠端連線"}`，再由 Reasoner 驗證並交 ToolRegistry handler 執行一次。派發結果只觸發應用程式擁有的固定 feedback，不代表遠端連線已實際建立；M5 MQTT 階段才另行定義真實 broker、topic 與 payload，且外部業務 response 仍須另經 buffer／`read`，不作為 handler return。
- **observing（觀察接續路徑）**：僅在需要辨識眼前物件種類時，模型輸出 `intent="look"`；child/Core 忽略模型 `text`，Reasoner 映射為固定準備語「我看一下。」的 Speak action，完成後進下一個 look-only perception turn。Look worker 取得 Camera／Vision 物件觀察結果（如 `OBS_BOOK`、`OBS_CUP` 或空偵測 `OBS_EMPTY`），再交原 Conversation 以 `speak`/`end` 有據回答先前問題，不捏造未提供的顏色或閱讀內容能力。Look 不經 ToolRegistry，也不以工具派發結果代表視覺觀察。

三條路徑都採「模型輸出兩欄有限意圖、Core 固定映射與驗證執行」；不要求模型產生 SDK 原生 function call，且 `automatic_tool_calling=false`。

### 2.2 結構化模型輸出與內部 v4 語意框架

區分**模型端兩欄輸出（model-facing schema）**與**內部 v4 四欄語意框架（internal v4 semantic frame）**：

1. **模型端兩欄 JSON（`requirements/m5tool/semantic-output-v1.schema.json`）**：
   Runtime `ResponseFormat.json` 與模型輸出固定為恰好兩個必填欄位的 object，拒絕額外 key／重複 key／非有限數值：

   ```json
   {"intent":"speak","text":"你好。"}
   ```

   - `intent` 為 `"speak" | "end" | "tool" | "look"`。
   - `text` 為 string（原始長度最多 4096 code points）。
   - **模型邊界文字規則**：
     - `speak`：`text` normalize 後必須非空，且最多 30 個 spoken characters。
     - `end`：`text` normalize 後可空，非空時最多 30 個 spoken characters。
     - `tool` 與 `look`：在兩欄 schema 下模型可能填入任意 `text`（例如過早宣稱已開啟連線或描述畫面），但該文字在 child parser／validator 邊界即被丟棄（轉換為空字串 `""`），**絕不作為 `SAFE_TEXT`、Display 文字、TTS 播音或命令參數**；實際語音與畫面回饋完全由應用程式固定字串控制。

2. **內部 v4 四欄語意框架（`ToolSemantic` 與 v4 IPC `RESULT.semantic`）**：
   為保持 v4 child 協定與 Core `ToolRegistry` 驗證邊界一致，child 在完成兩欄模型輸出驗證後，將其轉換為四欄內部語意 `ToolSemantic(intent, text, tool_name, arguments)`：
   - `speak` → `ToolSemantic("speak", normalized_text, "", {"message": ""})`
   - `end` → `ToolSemantic("end", normalized_text, "", {"message": ""})`
   - `tool` → `ToolSemantic("tool", "", "mock.send", {"message": "啟用遠端連線"})`
   - `look` → `ToolSemantic("look", "", "", {"message": ""})`

   此四欄結構是 Core／child 內部契約：`tool_name`（`"mock.send"`）與 `arguments.message`（`"啟用遠端連線"`）完全由程式碼固定產生，**並非由模型生成**。Parent／Reasoner 的 `validate_tool_semantic` 仍對四欄結構、跨欄位互斥、來源限制（`source="look"` 只允許 `speak | end`）、capability 開關及已註冊工具（`tool_name == "mock.send"`、normalized `message` 非空且 `<= 40` code points）執行完整防禦驗證，確保任何非法內部語意或未授權工具名稱在進入 handler 前即被拒絕。

### 2.3 模型 prompt（選定 c2）與 ASR 提示詞方向

先前的長版四欄 prompt 在真實 Gemma 上超出新 Conversation 首輪 `runtime_prefill_tokens <= 128` 門檻；依 USER 裁定，M5.tool 採用精簡兩欄 **c2** 產品 prompt（含既有溫暖自然、稍帶幽默人格，首輪實測 prefill 約 93–96 tokens）：

> 你是「雪板」，用繁體中文說完整短句，20字內，溫暖自然，稍帶幽默。只輸出含 intent 和 text 的 JSON。要求啟用遠端連線選 tool；辨識眼前物件選 look；問顏色選 speak，回答無法辨識；明確結束對話選 end；其他選 speak。

固定規則與診斷歷史邊界：
- 實際 prompt 與兩欄 schema 由 Developer 實作成固定產品資產（`M5_SYSTEM_PROMPT` 與 `requirements/m5tool/semantic-output-v1.schema.json`），不在模型 prompt 中附帶動態 registry dump、handler callable、credential 或私有識別資料。
- **診斷歷史記錄**：在單次實機 c2 診斷中，正向換句話說（「幫我打開遠端連線」）選對 `tool`，否定請求（「先不要啟用遠端連線」）選了 `end` 而非 `speak`。依 USER 決定，該否定句已移出本輪對話與測試驗收範圍，僅保留於開發診斷歷史，不列為現行驗收條件或修正門檻。
- **Whisper ASR 提示詞方向**：未來 M5 產品配置將 Whisper `initial_prompt` 改為固定字串 `遠端連線`（取代舊詞表，不回寫已 Accepted 的 ALPHA 證據）。依 USER 指示，本階段移除專用「啟用遠端連線」ASR 單句測項，不新增 ASR 詞彙測試矩陣。
- Startup 與測試情境不自動計算或驗證 prompt／schema／text SHA-256 digest；需要確認工作站與 Pi 檔案一致性時，僅在傳輸邊界執行一次獨立檢查。

## 3. 工具派發與固定回饋

M5.tool 的唯一註冊工具為 `mock.send`，描述：「模擬派發固定遠端連線命令；只記錄一次派發，沒有外部設備或 MQTT 網路副作用」。
Core 將模型的 `intent="tool"` 固定映射為 `tool_name="mock.send"` 與 `arguments={"message": "啟用遠端連線"}`（不接受模型自由指定訊息）。
Mock fixture 控制 success、已知 dispatch failure、可取消等待；這些控制不提供給模型。
驗證不執行 IO；派發只由既有 Tool worker 進行，且單次合法 `tool` 意圖只執行一次，不能由 Reasoner／SDK 呼叫 handler。

- `ActionCompleted(tool, ok)`：代表固定命令（`mock.send("啟用遠端連線")`）已派發成功，**不代表遠端連線已實際建立**。
- `ActionCompleted(tool, error)`：沒有確認派發成功；不推定外部未執行，也不自動重送。
- handler return 不送給模型，也不作為外部 response。M5 真實 MQTT 外部回應與實際連線狀態另經 buffer／`read` 處理。

Composition root 對新 profile 注入固定 tool-feedback policy；SM 不自行讀取 LLM prompt
或猜測 profile。SessionContext.action_phase 增加 `tool_feedback`，in-flight phase 增加
`action_tool_feedback`；仍使用既有 ActionCompleted，不增加 Event Bus event 型別。

**SM 新增有限的 `tool_feedback` ACTION phase：**

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
<= engine_context_tokens` 判斷。M5.tool 保留 M4B 的新 Conversation 首次推論
`runtime_prefill_tokens <= 128` 產品限制；`conversation_revision == 0` 且量得
`>128` 時，在 GENERATE 前走 E1，不把它當作使用者輸入過長或 context replacement。
後續 revision 不套此首輪限制，仍須通過完整 context admission。實際 prompt 若無法
容納首次合法 listen，回 Designer 修正 profile，不假裝測過或默默加大。

Look 成功輸入格式固定為 application-owned wrapper，facts 以 JSON string encoding 保留邊界：

```json
{"source":"look","status":"ok","facts":"偵測到一本書。","instruction":"依本次觀察直接回答先前問題；只說物件種類；沒有物件時繼續對話。"}
```

不加入虛構使用者語音、不重送全部 history。Look 能力對應物件種類觀察（如 `OBS_BOOK`、`OBS_CUP` 與空偵測 `OBS_EMPTY`）：物件問題選 `look` 後，在同一 Conversation 依觀察有據回答物件種類，不宣稱能閱讀文字內容，且空偵測時以 `speak` 繼續對話；詢問顏色等未提供屬性時應選 `speak` 誠實說明無法辨識。一次 Look 後（`source="look"` 輪）只允許 `speak`／`end`；若模型仍選
`look`／`tool`，按已送出推論的 invalid semantic 路徑處理，不自動重試工具。

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
- 模型輸出採兩欄 JSON（`intent`, `text`），由 `IncrementalM5ModelParser` 解析：只有在已解析並鎖定 `intent="speak"` 或 `"end"`，且 `text` 欄位完成正規化與 `<= 30` spoken characters 驗證（`"speak"` 必須非空）時，才將解碼後的 `text` 作為 `SAFE_TEXT` 發出。若 `"text"` 先於 `"intent"` 到達則先緩存，待鎖定 `"speak"`／`"end"` 後才發出，不假定 JSON key 順序。
- `intent="tool"` 與 `"look"` 在兩欄模型輸出中即使含有非空 `text`，也**絕不輸出 `SAFE_TEXT`**，且在轉為內部四欄 `ToolSemantic` 時將 `text` 清空（`tool` 固定填入 `tool_name="mock.send"`、`arguments={"message": "啟用遠端連線"}`），不會成為 Display 文字或 TTS 播音。
- 若另行對內部四欄語意做串流／完整性檢查（`IncrementalToolSemanticParser`／`validate_tool_semantic`），當已鎖定 `speak`／`end` 後續欄位卻出現非空 `tool_name`／`arguments.message` 違反互斥時，報 `INVALID_SEMANTIC` 並依 R2 取消播音，不能派發工具。
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

先在 Pi 的真實 Gemma／LiteRT-LM 上驗兩欄 JSON schema（`intent`, `text`）與選定的 c2 prompt 是否可產出四種合法語意，並量測
c2 prompt＋look facts 的 native rendered tokens。若 schema 不被 runtime 支援，或
在既定 context／output reserve 內無法容納，回 Designer 修正此 profile 的具體契約；
不能以手寫關鍵字分類、另一模型或默默縮減既有對話上下文宣稱 M5.tool 通過。

新能力 prompt 可能改變首輪 prefill 與反應時間。在 Pi 上以實際產品路徑記錄新
Conversation 首次推論及同 Conversation 後續推論的 `runtime_prefill_tokens`、首個安全文字
或語意 terminal 等待時間；分別看 answering、dispatching、observing 的直接影響。
以固定、精簡的 c2 兩欄能力 prompt 維持首輪 `<=128`，並驗證觀察有據回答。若無法兼顧合法首輪與真實模型
選擇品質，回 Designer 裁定修訂內容；分 turn 啟用目前不是已核准的實作
捷徑。第二 turn 的低 prefill 不能代替首輪體驗證據，也不能以
額外隱藏推論或假 prewarm 繞過既有生命週期。

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
冒寫執行 PASS。架構 delta 已落定，可進 Test Spec；不要求先完成 MQTT 或 VLM 研究。
