---
requestor: Reviewer
owner: Designer
status: Resolved
---

# IR_review_M5_TOOL_I — M5.tool 設計與 M5～BETA 里程碑跨文件審查

## 1. 審查範圍與價值檢查

本單審查 Designer 本輪提出的 M5～BETA 修訂：[`milestone.md`](../../milestone.md)、
[`milestones/M5.md`](../../milestones/M5.md)、[`milestones/M6.md`](../../milestones/M6.md)、
[`implement/ch_m5_tool.md`](../../implement/ch_m5_tool.md)、[`protocol.md` §7](../../protocol.md#7-m5tool-llm-protocol-v4)、
[`reviews/AR_impl_M5_TOOL_I.md`](../AR_impl_M5_TOOL_I.md)，以及直接連動的
[`milestones/M7.md`](../../milestones/M7.md) 與 [`milestones/BETA.md`](../../milestones/BETA.md)。

依 `AGENTS.md` 價值／風險原則，已剔除無實際產品失敗風險的項目（如 child 內部物件參照擦除證明、
未開線的 `ALPHA_R1` 用語微調與純索引表更新），僅保留會導致**實際執行失敗、測試規格分歧或違反現行工作原則**的項目。

---

## 2. Findings（同一 scope 合併提出）

| ID／等級 | 依據、位置與可重現差異（預期 vs 實際） | 產品與實作影響 | 首選修正／最低驗收 |
| :--- | :--- | :--- | :--- |
| **B1／Blocking** | **M5.tool Admission、模型輸入格式與 Streaming 條件缺口**<br>位置：[`ch_m5_tool.md` §2.2、§3、§4.2、§5](../../implement/ch_m5_tool.md#22-結構化模型輸出)、[`protocol.md` §4.3、§7.2](../../protocol.md#7-m5tool-llm-protocol-v4)、[`ch_m4b_llm_production.md` §5.2](../../implement/ch_m4b_llm_production.md#52-token-decisions)<br>1. **`user_tokens` 與 wrapper 混算**：`ch_m5_tool.md` §3 要求「Listen 的使用者長度限制先對原 utterance 執行，status wrapper 再組入實際 native admission；不讓系統提示吃掉使用者限額」，§4.2 規定 Look 輸入為最長 512 code points 的 JSON wrapper。但 `protocol.md` §7.2 規定 `MEASURE` 沿用 §4.3（僅傳單一 `text`），child 對該 `text` 計算 `user_tokens`。若傳入已包裝字串，`MEASURED.user_tokens` 會計入 wrapper，導致 Look 輪因 `user_tokens > 32` 被誤判 R1 拒絕，且帶 `last_dispatch_status` 的 listen 輪被系統提示吃掉 32-token 限額。此外 §3 未定義帶 `last_dispatch_status` 時的 listen model-facing 確切格式。<br>2. **首輪 `runtime_prefill_tokens <= 128` E1 常數衝突**：`ch_m4b_llm_production.md` §5.2 規定首輪 `runtime_prefill_tokens > 128` 直接判 E1；`core-m5-tool-001` 加入四種 intent 與工具定義後首輪 prefill 超過 128 tokens，未明定解除該常數會使首輪直接進 E1。<br>3. **Streaming `SAFE_TEXT` 欄位順序歧義**：§2.2 固定 JSON 範例為 `intent -> text -> tool_name -> arguments`，但 §5 寫「鎖定 intent=speak／end、空 tool 欄位不矛盾時，才能將解碼後的 text 作為 SAFE_TEXT」，易被實作為等待 `text` 之後的 `tool_name`／`arguments` 解析完才發 `SAFE_TEXT`，使預設順序下 streaming 失效。 | 1. Look 輪次與帶派發狀態的語音輪次在 admission 被誤拒，或首輪觸發 E1。<br>2. Tester 與 Developer 對 listen+status 輸入格式及 streaming 發送時機產生規格分歧。 | 見 §3.1 可直接採用文字。<br>**最低驗收**：`ch_m5_tool.md` 與 `protocol.md` §7 對齊單一輸入格式、token 判定與 streaming 條件；M5.tool Test Spec 覆蓋帶 `last_dispatch_status` 的 listen、Look admission 與 speak streaming。 |
| **B2／Blocking** | **`BETA.md` 與 `M7.md` 未同步 M5～BETA 範圍修訂與 `AGENTS.md` 原則**<br>位置：[`BETA.md` §1.1–§1.2、§3–§5](../../milestones/BETA.md#1-範圍beta-scope)、[`M7.md` §9.2、§9.4](../../milestones/M7.md#92-相依)，對照 [`milestone.md` §1.2–§1.4、§2](../../milestone.md#12-階段定案原則)、[`M5.md` §1](../../milestones/M5.md#1-已確認決策)、[`M6.md` §1、§2.4](../../milestones/M6.md#1-已確認流程)<br>1. **強制綁定 Wake 與已刪除章節**：`milestone.md` §1.3.1／§2 與 `M5.md`、`M6.md` 已固定「Wake 移出目前工作，BETA 前重新評估是否加入，不預設必做」並刪除舊 `M6 §8.4` 20-session soak；但 `BETA.md` §1.1、§4（`BETA-T-003`、`BETA-T-005`）、§5.2 仍強制要求 `Voice wake daemon`、`三種入口完整 session` 並引用已不存在的 `M6 §8.4`。<br>2. **保留額外角色互簽 Gate**：`BETA.md` §3.1／§3.2 與 `M7.md` §9.2 仍要求 `TR_spec_BETA_I Resolved`（Designer 簽核 Test Spec）與 `CR_BETA`（Designer Code Review Gate），違反 `AGENTS.md` 與 `milestone.md` §1.2／§1.4「唯一交付流程為 `Design → Test Spec → Developer → Verify`，不得插入角色互簽或文件核准 gate」。<br>3. **保留 hash／checksum 測項**：`BETA.md` §1.2／§4（`BETA-T-007`）／§5.2 與 `M7.md` §9.4 仍把 `checksum` 與 `config hash` 列為正式測項或人工 checklist 條件，違反 `AGENTS.md` 與 `milestone.md` §1.4 不將 digest／hash 作為測項斷言的原則。 | `milestone.md` §1.3／§2 將 `BETA.md` 列為契約來源，但 `BETA.md` 與 `M7.md` 保留舊版強制 Wake、角色互簽 gate 與 hash 測項，與現行權威直接衝突。 | 見 §3.2 可直接採用文字。<br>**最低驗收**：`M7.md` 與 `BETA.md` 同步為「已納入能力收斂（Wake 依 BETA 前決策條件式納入）」、無例行互簽 gate、無 hash／checksum 測項。 |
| **A1／Advisory** | **`AR_impl_M5_TOOL_I` 補充 `arch.md` §4.5 與 §4.8 連動節次**<br>位置：[`AR_impl_M5_TOOL_I.md` §3](../AR_impl_M5_TOOL_I.md#3-建議可直接採用的架構文字)、[`arch.md` §4.5、§4.8](../../arch.md#45-狀態轉移表)<br>`AR_impl_M5_TOOL_I` 請 Architect 修改 `arch.md` §2.7、§2.8、§4.6，但 `arch.md` §4.5 轉移表寫死 `ACTION primary \| ActionCompleted(kind∈{speak,tool}) + KEEP_NEXT -> PERCEPTION`，且 §4.8 寫死 `default_perceptions`「為 SM 唯一依 action Fact status 分歧的決策點」。 | 若 Architect 僅修改 §2.8／§4.6，`arch.md` 內部 §4.5／§4.8 會與新增的 `tool_feedback` phase 產生字面矛盾。 | 見 §3.3 可直接採用補充句，加註於 `AR_impl_M5_TOOL_I.md` §3。 |

---

## 3. 建議可直接採用的修訂文字

### 3.1 對應 B1：`ch_m5_tool.md` §3、§4.2、§5 與 `protocol.md` §7.2

1. **`ch_m5_tool.md` §3 末段與 §4.2（Listen + `last_dispatch_status` 格式與 Token Admission 分界）**：
   > - 一般無前輪派發狀態的 `listen` 輪次，model-facing `text` 為 normalized utterance；若帶前輪派發狀態，固定包裝為：
   >   `{"source":"listen","last_dispatch_status":"ok|error","text":"<normalized utterance>"}`
   > - `listen` 的 20 normalized code points 與 `user_tokens <= 32` 限制只針對未加 wrapper 的原 normalized utterance；當本輪帶 `last_dispatch_status` 時，`MEASURE` 以 `user_text` 傳入原 normalized utterance 計算 `user_tokens`，並以完整 wrapper 作為 `text` 計算 `rendered_incremental_tokens` 與 `runtime_prefill_tokens`（無 wrapper 時 `user_text` 與 `text` 相同）。
   > - `look` 輪次只檢查 facts `<= 512` normalized code points 與 `current_kv_tokens + rendered_incremental_tokens + output_reserve_tokens <= 1024`，不套用 `listen` 的 20 字與 `user_tokens <= 32` 限制（`MEASURE` 的 `user_tokens` 僅作觀測記錄）。
   > - `core-m5-tool-001` 不套用 M4B 的首輪 `runtime_prefill_tokens <= 128` E1 常數，統一以 `1024` context equation 與 §7 實測容量為準。

   （對應在 `protocol.md` §7.2 補一句：`v4 MEASURE 可帶 optional "user_text"（預設等於 "text"），child 以 "user_text" 計算 user_tokens，以 "text" 進行 native render 與 ticket 實值綁定。`）

2. **`ch_m5_tool.md` §5 第二點（Streaming `SAFE_TEXT` 條件）**：
   > - M5.tool semantic parser 只有在已解析並鎖定 `intent ∈ {speak, end}`，且**目前已出現**的 `tool_name`／`arguments` 欄位無非空矛盾時，才能將解碼後的 `text` 作為 `SAFE_TEXT` 串流輸出；若 `text` 先於 `intent` 到達則先緩存，不假定 JSON key 順序。`tool`／`look` 不輸出 `SAFE_TEXT`。若 `text` 之後出現的欄位違反互斥或完整 schema 不合，於 terminal 判定 `INVALID_SEMANTIC` 並依 R2 取消播音。

### 3.2 對應 B2：`docs/milestones/M7.md` 與 `docs/milestones/BETA.md`

1. **`docs/milestones/M7.md`**：
   - §9.2 第 5 點改為：
     > * M7 Accepted 後，進入 `BETA` 已納入能力的產品收斂 Gate；M7 通過不推定 BETA 通過。流程依 `Design → Test Spec → Developer → Verify` 執行，不插入額外角色互簽 gate。詳見 `docs/milestones/BETA.md`。
   - §9.4 第 2 點末項改為：
     > * 人工 checklist 記錄硬體、resolution、資產 revision、時間與 pass / fail（不於測項或 startup 自動計算／驗證 config hash）；人工結果不取代 ownership、timeout 與 cleanup 自動化測試。

2. **`docs/milestones/BETA.md`**：
   - 標題與定位、§1.1 改為「**已納入能力的產品收斂 Gate**」，表格對齊現行階段：
     - `M4 (= ALPHA 基礎)`：Button、Listen / ASR、Reasoner / LLM、Speak / TTS、M4c Session Display、離線 session
     - `M5.tool + M5`：真實模型能力選擇、固定派發回饋、MQTT 發送與外部訊息 `read` 流程
     - `M6`：Camera / YOLO / 結果整理與 `look` 接續回答（Wake 依 BETA 前產品決策：若決定納入才驗 wake daemon 與第三入口，未納入則排除）
     - `M7`：正式 Display UX、StatusBar、Main、Fullscreen、icons、動畫、OLED 保護
   - §1.2、§3.2、§4、§5.2：
     - 移除 `TR_spec_BETA_I Resolved` 與 `CR_BETA` 簽核條件，改為依 `Design → Test Spec → Developer → Verify` 於 Pi 對相同待提交內容完成驗證。
     - 將 `BETA-T-003` 改為 `M6 Look / Vision regression（若 BETA 前決策納入 Wake 則含 wake）`；`BETA-T-005` 移除 `M6 §8.4` 引用，改為依 BETA 實際風險設定的連續多 session 穩定性與資源釋放檢查。
     - 移除 `BETA-T-007`（checksum 測項）與 §5.2 checklist 的 checksum 逐項核對，改為保留組件版本、來源、授權與已知限制清單（必要內容核對僅由 operator 於移轉邊界獨立執行）。

### 3.3 對應 A1：`docs/reviews/AR_impl_M5_TOOL_I.md` §3

於 `AR_impl_M5_TOOL_I.md` §3「§2.8 與 §4.6 — Tool 派發後的有限 feedback phase」末尾補入一句：

> 同步更新 §4.5 狀態轉移表（支援 `tool_feedback` 的 profile 於 `ACTION primary` 完成 `tool + KEEP_NEXT` 時先進 `ACTION tool_feedback`，待 feedback `ActionCompleted(speak)` 後再進 `PERCEPTION`）與 §4.8（除 `default_perceptions` 外，允許 `tool_feedback` 依 primary `ActionCompleted(tool).status` 選擇固定回饋語句並記錄單輪 `last_dispatch_status`；`tool_feedback` 若 `status=error` 仍依 `default_perceptions` 進下一輪 `PERCEPTION`）。

---

## 4. Owner 回覆位置

請 Designer 於此處回覆採用或等價修正、實際更新檔案與節次，並將狀態改為 `Revised` 交 Reviewer 複審。

### Designer 回覆（2026-10-23）

- **B1 採用**：`implement/ch_m5_tool.md` §2.3、§3、§4.2、§5 固定 listen status
  wrapper 與模型解讀、原 utterance 的 20 字／32-token 邊界、Look 的獨立 admission、
  M5.tool 不繼承 M4B 首輪 128-token E1，以及可在後續空工具欄位尚未到達時輸出的
  SAFE_TEXT 條件。`protocol.md` §7 的 v4 MEASURE 增 `user_text`，原文計
  `user_tokens`、完整 wrapper 做 native render／ticket，child 驗兩者實值相符；
  後續欄位違反語意互斥時以 `INVALID_SEMANTIC` 走 R2，工具不得派發。
- **B2 採用**：`milestones/M7.md` §9.2／§9.4 與 `milestones/BETA.md` §定位、§1、
  §3–§6 改為已納入能力的收斂，Wake 只在 BETA 前決定納入才驗；移除舊簽核 gate、
  `M6 §8.4` 死引用與 `BETA-T-007` checksum 測項。必要內容核對留在獨立移轉／診斷邊界。
- **A1 採用等價文字**：`AR_impl_M5_TOOL_I.md` §3 補列 Architect 應同步修改
  `arch.md` §4.5／§4.8，說明 `tool_feedback` phase 與 primary status 的固定回饋，
  保留 continuing action error 的 `default_perceptions` 路徑。

請 Reviewer 依上述三項與直接影響面複審；本單維持 `Revised`，由 Reviewer 判定結案。

---

## 5. Reviewer 複審結案（2026-10-23）

- **Finding Disposition**：
  - **B1 — Resolved**：`implement/ch_m5_tool.md` §2.3／§3／§4.2／§5 與 `protocol.md` §7.2／§7.4 已對齊帶 `last_dispatch_status` 的 listen JSON wrapper、v4 `MEASURE.user_text` 與完整 `text` 的分開計數、Look 獨立 admission、不沿用 M4B 首輪 128-token E1 常數，以及不等待未到達空工具欄位的 `SAFE_TEXT` 串流與 R2 取消規則。
  - **B2 — Resolved**：`milestones/M7.md` §9.2／§9.4 與 `milestones/BETA.md` 已同步為「已納入能力的產品收斂 Gate」，Wake 改為依 BETA 前決策條件式納入，並移除 `M6 §8.4` 舊引用、`TR_spec_BETA_I`／`CR_BETA` 例行互簽 gate 與 `BETA-T-007`／`config hash` 測項斷言。
  - **A1 — Resolved**：`reviews/AR_impl_M5_TOOL_I.md` §3 已補入 `arch.md` §4.5 與 §4.8 的同步修訂說明。
- **Status**：`Resolved`（移入 `docs/reviews/history/IR_review_M5_TOOL_I.md`）。
- **Next owner**：**Architect**（依 `status/current.md` 與 `reviews/AR_impl_M5_TOOL_I.md` 處理 architecture delta 後交 Tester 建立 M5.tool Test Spec）。
