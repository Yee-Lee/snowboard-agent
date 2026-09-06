---
requestor: "Reviewer"
owner: "Architect"
status: "Revised"
severity: "Blocking"
---

# AR_review_M4B_I — M4B/M4C ownership and lifecycle relaxation

日期：2026-09-06。審查範圍為 `AR_impl_M4B_II` 的 Architect 修訂、
`docs/arch.md` 對應 delta，以及其直接影響的 M4B-MVA-002、M4C、Display 與既有
session convergence 契約。本輪不重開 model selection、M4A qualification、001 歷史、
queue 數值或 UX 文案。

## 結論

**Rejected — Blocking 4 / Advisory 0。**

四項方向本身均可成立，但目前放寬文字留下互斥實作：pre-open 同時被要求於 SM begin
才建立、streaming 未獲得跨 THINK/ACTION 的資料與 ownership 路徑、pre-session 顯示被綁到
不存在的 `StateChanged`，而「唯一退出路徑」排除了既有 Level 3。這些會改變 session
隔離、Fact/state transition、使用者可觀察行為或 fatal recovery，不是措辭偏好。

另依 `AR_impl_M4B_II` 的 `activation` 與 M4B-MVA-002 gate，EFFICIENCY 結果及 Designer
selected adoption 尚未出現；因此本單即使先修正文義，也不得在 selected proposal 到位前
標記 `Resolved` 或授權 production implementation。

## AR-M4B-I-01 — Conversation lifetime 與 end convergence 仍有兩套互斥時序

### 權威依據與矛盾

- `AR_impl_M4B_II` Decision 1 要允許 SM begin 前存在 unclaimed clean Conversation，並由
  SM begin 原子綁定；M4B-MVA-002 `Readiness and session lifecycle` 也明定 pre-open 與
  on-demand open 都是合法候選。
- `arch.md` §4.1 卻寫成「SM begin 觸發建立」且 Conversation lifetime 與 session 共生；
  §4.6 THINK Entry 再次寫成 begin 觸發 Conversation 建立。照字面實作會禁止 pre-open，
  或讓實作者忽略架構的 lifetime 句而在 session 前建立同一物件。
- `arch.md` §4.6 ERROR Entry 新寫「Conversation close 流程完成後才執行 in-flight 收斂」；
  但已核准的 `ch_m4b_llm_production.md` §3 與 `AR_impl_M4B_I` Designer 結案固定順序為：
  先登記 end intent／拒新 admission，再取消或等待 active open/generate，取得 terminal/join
  proof 後才 native close，最後才清 SM tracking。直接先 close 仍被 active operation 使用的
  Conversation 會造成 cleanup race；四路各自解讀也會破壞一致收斂。

### 直接修訂建議

架構應區分「未被產品 session claim 的 clean prepared object」與「已綁定 session 的
Conversation」，並只固定 claim、隔離及收斂順序，不固定由哪個 component 建立。請直接：

1. 以以下段落取代 §4.1 `Lifetime 契約`：

> Product session 至多 claim 一個 Conversation。Implement 可在 SM begin 前準備一個未綁定、
> 不含 user/session history 的 clean Conversation；SM begin 必須原子地綁定相容的 prepared
> object，或按需建立後綁定。綁定後 Conversation 才與該 session 共生，且不得被其他 session
> 使用。prepared/claimed object 的 component owner 與初始化 API 屬 implement。

2. 將 §4.6 THINK Entry 的「觸發 Conversation 建立」改為：

> SM session begin 觸發取得本 session 的 Conversation：原子綁定相容的 prepared object，
> 或按需建立後綁定；取得完成前不得開始 generate。控制工作不阻塞 SM inbox。

3. 以同一段落取代 §4.6 ACTION Exit / ERROR Entry 與 §4.7 四路的 Conversation 順序敘述：

> SM end 先登記 end intent 並拒絕新 admission，再依 §6.5 收斂 active open/generate；取得
> terminal/join proof 後完成 Conversation close，最後才清 session tracking 或接受新 session。
> rest、interrupt、error、shutdown 與 late completion 均遵循此順序；具體 component/API
> 屬 implement。

### 影響與最低驗收

影響 session isolation、cancel/close safety、late completion 與下一 session admission。
修訂後不得再有「begin 必然建立」或「close 完成後才開始 in-flight 收斂」文字；rest、
interrupt、error、shutdown 四路必須共用 end-intent → active convergence → close proof →
clear/admit 的單一順序，且明定 unclaimed object 不含產品 session context。

## AR-M4B-I-02 — streaming fragment 尚未取得可實作的 cognition → action 架構路徑

### 權威依據與矛盾

- `arch.md` §2.7、§4.5、§4.6 固定 Reasoner 每 turn 產一個完整 `LLMResponse`，SM 在 THINK
  Exit 驗證成功後才進 ACTION，ACTION Entry 才啟動 action worker。
- 新增的 §2.8 只說 full-response / streaming 是 `speak` action 內部 delivery strategy；
  它沒有說明仍在 THINK 中的 incremental semantic text 如何合法進入尚未啟動的 speak，
  也沒有定義 generation、speak 與 SM in-flight/cancel 的共同 ownership。
- M4B-MVA-002 與 M4C 要求 `Begin/Text/Complete|Failed`、同一 speak action、terminal failure
  取消 queued/in-flight speech。依現行架構，實作者只能選擇「等完整 LLMResponse 後才播，
  實際沒有 streaming」或「THINK 期間繞過 SM 提前啟動 action」；兩者分別違反產品需求或
  SM 唯一派發／追蹤邊界。

### 直接修訂建議

保留每 turn 一個 terminal Fact 與一個 speak operation，但架構須明確授權其窄 streaming
路徑。請直接以以下語意取代 §2.8 新增段落，並同步 §4.5/§4.6：

> M4C 的 THINK Entry 可由 SM 建立一個綁定 `(session_id, turn_id, correlation_id)` 的單次
> streaming-speak control，並交給本 turn Reasoner。第一個經 Reasoner 判定可交付的 semantic
> text 由該 control 啟動唯一 speak worker；SM 在 THINK 期間即把該 worker 納入同一 turn 的
> in-flight tracking。後續有序 fragment 只進同一 worker。fragment 是 operation 內資料，
> 不是 Fact、獨立 action 或新 turn，也不觸發 state transition。若 speak 在 THINK 期間先完成，
> 其 terminal 只形成 SM private completion notice；在 semantic terminal 驗證前不得發布
> `ActionCompleted`。
>
> Reasoner terminal `LLMResponse` 仍是一 turn 唯一 cognition Fact。若已啟動 streaming speak，
> terminal response 必須驗證為同一 speak intent；驗證通過才由 THINK 進 ACTION，並在 ACTION
> 等待該既有 speak worker 的 terminal。只有 terminal semantic validation 與 speak terminal
> 都成功，才發布並接受唯一 `ActionCompleted(status=ok)`、再進下一 turn。invalid/failed terminal、
> intent 不一致或 interrupt 必須共同取消 generation、queue、TTS 與 playback，結束 dirty
> session，且不得接受或發布正常成功。M4B full-response 不啟用此 control，維持 terminal
> `LLMResponse` 後才啟動 speak。確切 port、chunk 與 backpressure 數值屬 implement。

§4.5 的 THINK 完成條件須同步接受「matching streaming speak private completion 只記錄、
不提前轉移」；§4.6 ACTION Entry 須改成「若本 turn streaming speak 已啟動則沿用，否則依
`LLMResponse` 啟動」。不得把 `ActionCompleted` 列為 THINK 可接受的公開 Fact，也不得只改
§2.8 留下相反的 transition table。

### 影響與最低驗收

影響 SM 派發權、Fact cardinality、cancel、false success 及跨 turn 污染。最低驗收為：
`arch.md` 可唯一回答 fragment 何時可流動、誰授權／追蹤、何時可 transition／成功、terminal
failure 如何收斂；同時維持一 turn 一個 terminal `LLMResponse`、一個 speak operation，且
fragment 永不成為 Fact 或獨立 action。

## AR-M4B-I-03 — pre-session preparing/error 與「唯一 StateChanged」互相不可實作

### 權威依據與矛盾

- `display_spec.md` 是使用者可觀察 Display 行為的權威；其 §1.3、§3.2、§4.1 目前要求未列
  畫面不屬產品行為、boot/shutdown 為 Fullscreen Blank，且 SM 初始 IDLE 不發布虛構
  `None -> IDLE`。`ch08_display_arbiter.md` §6 也由 owner startup seed IDLE，另有 lifecycle
  fullscreen client 與 sanitized error observer，不全由 `StateChanged` 觸發。
- 新 `arch.md` §4.3 同時允許 pre-session preparing/error、宣告 `StateChanged` 是唯一觸發源，
  又把 UX 時機／模式全交 implement。Pre-session 尚無架構 state transition；startup failure
  也可能發生在 SM 可進 ERROR 前。因此 preparing 無合法 trigger，error detail 的既有 observer
  又被「唯一」排除。若 implement 自行選 fullscreen/status、Blank/preparing，則同一產品 profile
  會有不同使用者可見行為。

### 直接修訂建議

架構只固定角色與資料來源邊界；可觀察內容仍由 `display_spec.md` 決定。請以以下段落取代
§4.3 新增的「系統狀態顯示邊界」全文：

> 系統狀態提示必須由 §5.3 三角色經 Arbiter 呈現；對話 state 投影使用 `StateChanged`，
> startup/shutdown 使用 lifecycle client，sanitized error detail 使用 error observer。
> `display_spec.md` 決定合法畫面、時機、文案與 Normal/Fullscreen 模式。架構不為顯示新增
> SM state。若 M4C 採用 pre-session preparing，Designer 必須先修訂 display spec 並定義其
> lifecycle trigger；在該修訂核准前，boot 維持現有 Fullscreen Blank。

### 影響與最低驗收

影響 M3 已核准 Display profile、M4C startup/error acceptance 與 privacy source。最低驗收為
移除 `StateChanged`「唯一觸發源」及 implement 可自行決定產品畫面的授權；arch、
display_spec、Ch 8、M4/M4C 對 boot Blank 或 preparing 的當前狀態必須只有一種答案，且
pre-session/error 各有實際存在的權威 trigger。

## AR-M4B-I-04 — launcher 外部化誤排除 fatal exit 與 M4C 交付責任

### 權威依據與矛盾

- 新 `arch.md` §5.4 寫「SM 的唯一退出路徑是 `ShutdownRequested`」，但 §6.4 明定 Level 3
  會讓 process crash，再由 systemd 重啟；Architect 回應又聲明 Level 3 不受影響。兩句無法同時
  為真。
- 同段寫 startup/restart 不屬 Snowboard App 範圍；M4C 與 ALPHA 卻要求 M4C 交付 explicit
  external launcher entry、驗證 shutdown/start again，且 ALPHA 不新增 systemd/supervisor。
  若把「App 範圍」解讀為整個產品交付範圍，launcher 可被兩個 milestone 都省略。

### 直接修訂建議

請以以下段落取代 §5.4 新增的「Launcher 外部化邊界」全文：

> App 主動要求的唯一 graceful exit 是 `ShutdownRequested` → convergence → process exit；
> §6.4 Level 3 fatal termination 仍是獨立非 graceful 出口。App process 內的 SM/RM 不決定或
> 執行 self-restart；重新啟動由 external launcher 負責。External 表示 process ownership
> 邊界，不表示免除產品交付：launcher artifact、start mode、restart policy 與 M4C/ALPHA
> 驗證責任依 milestone/deploy design 固定。

### 影響與最低驗收

影響 fatal recovery、exit classification 及 M4C/ALPHA 是否可操作。最低驗收為 `arch.md`
同時列出 graceful shutdown 與 Level 3 fatal exit，不再用「唯一退出路徑」涵蓋兩者；並明記
launcher 在 App process 外但仍須由 downstream design 指派交付與驗證 owner。

## Owner 一次回覆與複審範圍

Architect 請一次修訂上述四項並在 `AR_impl_M4B_II` 回覆每項落點。方向明確時採用首選文字
或完整等價語意，不需擴大選項。Reviewer 複審只核對本四項、其直接引用面及修訂新造成的
安全／session identity／state transition regression；不新增原可識別的低價值門檻。

四項通過後仍須等待 Designer 提供 POC 結果採用的單一 selected proposal，才能核對最終
design/plan delta 並結案。在此以前 `AR_impl_M4B_II`、M4B-MVA-EFFICIENCY 與
M4B-MVA-POC 保持未解除，Developer／Tester 不進場。

---

## Architect 回應（2026-09-06）

四項 Blocking 均採用首選文字或完整等價語意，逐項落點如下：

### AR-M4B-I-01 — 已採用

* **§4.1 Lifetime 契約**：採用首選文字——區分 unclaimed clean prepared object 與已綁定 session 的 Conversation；SM begin 原子綁定或按需建立；綁定後才共生，不得跨 session 使用；component owner 與 API 屬 implement。已移除「SM begin 觸發建立」。
* **§4.6 THINK Entry**：採用首選文字——「原子綁定相容的 prepared object，或按需建立後綁定；取得完成前不得開始 generate」。
* **§4.6 ACTION Exit / ERROR Entry / §4.7 表格**：四路統一為 end-intent → active convergence → terminal/join proof → Conversation close → clear tracking/accept new session 的單一順序。已移除「close 完成後才開始 in-flight 收斂」文字。

### AR-M4B-I-02 — 已採用

* **§2.8**：採用首選文字——M4C streaming-speak control 綁定 `(session_id, turn_id, correlation_id)`，SM 在 THINK 期間授權啟動唯一 speak worker 並納入 in-flight tracking；fragment 為 operation 內資料，不是 Fact/action/turn；speak 在 THINK 先完成只記 private notice，不提前發布 `ActionCompleted`。M4B 不啟用此 control。
* **§4.5 THINK→ACTION 行**：增加 streaming speak private completion notice 不提前轉移的備註。
* **§4.6 ACTION Entry**：改為「若本 turn streaming speak 已啟動則沿用，否則依 `LLMResponse` 啟動」。
* **不變**：`ActionCompleted` 不列為 THINK 可接受的公開 Fact；terminal `LLMResponse` 仍是一 turn 唯一 cognition Fact。

### AR-M4B-I-03 — 已採用

* **§4.3 系統狀態顯示邊界**：採用首選文字——對話 state 用 `StateChanged`、startup/shutdown 用 lifecycle client、sanitized error detail 用 error observer（三個資料來源）；`display_spec.md` 決定合法畫面/時機/文案/模式；架構不為顯示新增 SM state；M4C pre-session preparing 須先修訂 display spec 並定義 lifecycle trigger；在該修訂核准前維持 Fullscreen Blank。
* 已移除「唯一觸發源」及 implement 可自行決定產品畫面的授權。

### AR-M4B-I-04 — 已採用

* **§5.4 Launcher 外部化邊界**：採用首選文字——graceful exit 為 `ShutdownRequested` → convergence → process exit；Level 3 fatal termination 為獨立非 graceful 出口（兩者並存）；SM/RM 不 self-restart；external 表示 process ownership 邊界，不免除產品交付；launcher artifact/policy/驗證由 milestone/deploy design 固定。
* 已移除「唯一退出路徑」文字。

狀態改為 `Revised`，請 Reviewer（Requestor）複審。

---

## Reviewer 複審（2026-09-06）

**Rejected — remaining Blocking 2 / Advisory 0。**

本次只核對 AR-M4B-I-01～04、直接引用面與修訂造成的 regression，沒有新增 finding。
AR-M4B-I-03、AR-M4B-I-04 已完整通過；AR-M4B-I-01、AR-M4B-I-02 的主要方向已採用，
但各剩一個直接套用時產生的時序矛盾。請依下列文字一次修正，無需改動已通過部分。

| Finding | 複審結果 | 剩餘 Blocking |
| :--- | :--- | :--- |
| AR-M4B-I-01 | Partial | ACTION Exit / ERROR Entry 重複執行 §6.5；Shutdown 在收斂與 close 後才進 shutdown mode，期間未先拒絕新 wake，且同列再次執行 §6.5 |
| AR-M4B-I-02 | Partial | THINK 期間的「speak worker terminal」被改成 private notice，與 §6.3 worker 結束前必須發布 terminal Fact 的既有契約衝突 |
| AR-M4B-I-03 | Pass | 無；三種權威來源與現行 Boot Blank 邊界已唯一化 |
| AR-M4B-I-04 | Pass | 無；graceful / fatal exit 與 downstream launcher 責任已分開 |

### AR-M4B-I-01 剩餘修正 — 每條結束路徑只能收斂一次，shutdown 必須先封 admission

**實際矛盾：**

- §4.6 ACTION Exit 第一點已包含「依 §6.5 收斂」，下一點又要求「對本 session 剩餘
  in-flight 執行 §6.5」，形成兩次 convergence。
- §4.6 ERROR Entry 同樣在第一點完成 §6.5，下一點再執行一次。
- §4.7 Shutdown row 寫成「收斂 → close proof → 進 shutdown mode → §6.5 收斂」；這既
  重複收斂，也違反 §6.2 step 1 必須先進 shutdown mode、拒絕新 wake 的既有順序。

**請直接修正：**

1. §4.6 ACTION Exit 保留一個 sequence bullet，將目前前兩點合併為：

> SM end 先登記 end intent 並拒絕新 admission，再依 §6.5 一次收斂本 session 全部
> in-flight work（包含 active open/generate 及 streaming speak）；取得 terminal/join proof
> 後完成 Conversation close，最後才清 session tracking 或接受新 session。Rest、interrupt、
> error、shutdown 與 late completion 均遵循此順序；具體 component/API 屬 implement。

刪除緊接其後獨立的「對本 session 剩餘 in-flight 執行 §6.5」bullet；既有 clear tracking
與 `flush-to-wake` bullets 保留。

2. §4.6 ERROR Entry 同樣只保留一個 sequence bullet：

> SM end（若有活躍 session）先登記 end intent 並拒絕新 admission，再依 §6.5 一次收斂
> 本 session 全部 in-flight work；取得 terminal/join proof 後完成 Conversation close。
> 具體 component/API 屬 implement。

刪除其後重複的「對 in-flight 集合執行 §6.5」bullet。

3. §4.7 Shutdown row 直接替換為：

> `ShutdownRequested` / `SIGTERM` / `SIGINT`：SM 先進 shutdown mode 並拒絕新 wake；若有
> 活躍 session，再登記 end intent 並拒絕新 admission，依 §6.5 一次收斂全部 in-flight work；
> 取得 terminal/join proof 後完成 Conversation close。In-flight 集合空後停 dispatch loop，
> `main.py` 再依 Resource Manager 反向呼叫各模組 `stop()`（§6.2）。

**最低驗收：** ACTION Exit、ERROR Entry、Interrupt 與 Shutdown 每條都只出現一次 §6.5
convergence；Shutdown 在任何 await/convergence 前即拒絕新 wake；所有路徑仍維持
end intent → convergence → close proof → clear/stop，且新 session 不得在 close proof 前進場。

### AR-M4B-I-02 剩餘修正 — private notice 只能代表內部 stage 完成，不能代表 worker terminal

**實際矛盾：** `arch.md` §6.3 要求 worker 在 task return 前發布 terminal Fact；被 cancel 的
worker 才不發布 Fact。新 §2.8 若讓 speak worker 已 terminal/return、卻只留下 private notice，
會讓同一正常完成同時符合與違反 worker 契約。

**請直接修正：**

1. 將 §2.8 的句子：

> 若 speak 在 THINK 期間先完成，其 terminal 只形成 SM private completion notice；在
> semantic terminal 驗證前不得發布 `ActionCompleted`。

替換為：

> 若 delivery/playback stage 在 THINK 期間先完成，只形成 SM private completion notice；
> speak worker 保持 in-flight，不得 return，也不得在 semantic terminal 驗證前發布
> `ActionCompleted`。Terminal `LLMResponse` 驗證通過並進 ACTION 後，若 private completion
> 已記錄，speak worker 才發布唯一 `ActionCompleted` 並 return；若驗證失敗或發生 cancel，
> worker 依 §6.3 收斂且不發布正常 Fact。

2. §4.5 THINK→ACTION row 將「streaming speak 已先完成」改為「streaming speak 的
delivery/playback stage 已記錄 private completion」，避免把 private stage completion 誤寫成
worker/task terminal。§4.6 ACTION Entry 的「沿用既有 speak worker」可保留。

**最低驗收：** 正常 streaming speak task 無論內部 playback 先完成或後完成，都只在 ACTION
發布一次 `ActionCompleted` 後 return；THINK 只接收 private stage notice，不接收公開
`ActionCompleted`；invalid/cancel 路徑不發布正常 Fact，並與 §6.3 terminal Fact / task done
join 契約一致。

## 複審鎖定與 gate

Architect 只需修正上述兩個剩餘缺口並更新落點；下一次複審不重開 AR-M4B-I-03/04，
也不新增其他低價值要求。即使本單四項全數通過，`AR_impl_M4B_II` 的 activation 條件仍未
滿足：EFFICIENCY 結果及 Designer selected adoption 到位前，本單不得 `Resolved`，亦不授權
production implementation。

---

## Architect 二次回應（2026-09-06）

針對複審剩餘的兩項 Blocking（AR-M4B-I-01、AR-M4B-I-02），已全部依建議採用首選文字修訂完成：

### AR-M4B-I-01 剩餘修正 — 已採用

1. **§4.6 ACTION Exit (`kind=rest`)**：合併為單一 sequence bullet，依 §6.5 一次收斂本 session 全部 in-flight work（包含 active open/generate 及 streaming speak）；刪除重複的獨立 in-flight 收斂 bullet。
2. **§4.6 ERROR Entry**：合併為單一 sequence bullet，依 §6.5 一次收斂本 session 全部 in-flight work；刪除重複的獨立 in-flight 收斂 bullet。
3. **§4.7 Shutdown row**：修正為 `ShutdownRequested` / `SIGTERM` / `SIGINT` 先進 shutdown mode 並拒絕新 wake；若有活躍 session，再登記 end intent 並拒絕新 admission，依 §6.5 一次收斂全部 in-flight work；取得 terminal/join proof 後完成 Conversation close。In-flight 集合空後停 dispatch loop，`main.py` 再依 Resource Manager 反向呼叫各模組 `stop()`（§6.2）。

### AR-M4B-I-02 剩餘修正 — 已採用

1. **§2.8 Speak 執行語意**：採用首選文字——若 delivery/playback stage 在 THINK 期間先完成，只形成 SM private completion notice；speak worker 保持 in-flight，不得 return，也不得在 semantic terminal 驗證前發布 `ActionCompleted`。Terminal `LLMResponse` 驗證通過並進 ACTION 後，若 private completion 已記錄，speak worker 才發布唯一 `ActionCompleted` 並 return；若驗證失敗或發生 cancel，worker 依 §6.3 收斂且不發布正常 Fact。
2. **§4.5 THINK→ACTION 行**：將「streaming speak 已先完成」改為「若本 turn 有 streaming speak 的 delivery/playback stage 已記錄 private completion，該 notice 只記錄、不提前轉移，待 terminal 驗證通過才進 ACTION」。
3. **§4.6 ACTION Entry**：維持沿用既有 speak worker 邏輯。

狀態改為 `Revised`，提請 Reviewer 複審。

---

## Reviewer 二次複審（2026-09-06）

**Architecture amendment PASS — Blocking 0 / Advisory 0；status 維持 `Revised`，尚不結案。**

本次只驗收前次複審鎖定的 AR-M4B-I-01、AR-M4B-I-02 剩餘缺口，並確認
AR-M4B-I-03/04 已通過文字未被改動。未新增 finding。

| Finding | 結果 | 驗收證據 |
| :--- | :--- | :--- |
| AR-M4B-I-01 | Pass | §4.6 ACTION Exit 與 ERROR Entry 各只剩一個 §6.5 sequence；§4.7 Interrupt/Shutdown 各只收斂一次；Shutdown 在任何 convergence 前先進 shutdown mode 並拒絕新 wake，close proof 後才停 dispatch loop／reverse stop |
| AR-M4B-I-02 | Pass | §2.8 已把 private notice 限定為 delivery/playback stage completion；speak worker 保持 in-flight、不 return，terminal `LLMResponse` 驗證通過並進 ACTION 後才發布唯一 `ActionCompleted`；§4.5 同步使用 stage wording，符合 §6.3 Fact/task join |
| AR-M4B-I-03 | Pass（維持） | `StateChanged`、lifecycle client、error observer 三來源及現行 Boot Blank 邊界未回退 |
| AR-M4B-I-04 | Pass（維持） | graceful / Level 3 fatal exit 與 downstream launcher owner 邊界未回退 |

### Gate disposition

四項 architecture findings 已全部清零，Architect 無需再修改本輪架構文字。但依本單既有
closure lock 與 `AR_impl_M4B_II` front matter，`M4B-MVA-EFFICIENCY` 結果及 Designer 的單一
selected adoption proposal 尚未到位；因此目前只確認 architecture amendment PASS，不把本單
標成 `Resolved`、不移入 history，也不授權 production implementation。

待 Designer 提供 selected proposal 後，最終複審只核對該 proposal 是否落在本次已通過的
ownership、streaming、Display 與 launcher 邊界內；若沒有新的直接矛盾，即可直接
`Resolved` 並歸檔，不再要求 Architect 重做本輪四項修訂。
