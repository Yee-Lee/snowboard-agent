---
requestor: Designer
owner: Architect
status: Resolved
---

# AR_impl_M5_MQTT_I — pending external message 的確定性 read-only 排程

## 1. 請求與來源

USER 已確認 M5 MQTT 採低風險、單一來源的 perception turn：external message 在活躍 Session
到達時不打斷當前 operation；到下一個可進 listen 的安全 PERCEPTION 邊界，StateManager 若看到
pending message，將該輪確定性替換為 `read-only`，不並行啟動 listen。產品設計見
[ch_m5_mqtt §5](../../implement/ch_m5_mqtt.md#5-external-message--read--think)。

現行 `arch.md` §2.7、§4.6、§5.1 將 pending metadata 交 Reasoner，讓 Reasoner 在 THINK
決定後續 `next_perceptions` 是否含 read。若訊息在 ACTION／tool_feedback 期間到達，既有
`next_perceptions=(listen,)` 仍會先啟動一次 listen，無法滿足已確認行為。

此單只處理 scheduling ownership；不改 external buffer、read consume、current operation 收斂、
Look 流程、Conversation ownership或 payload 隱私，也不增加新的 review／sign-off gate。

## 2. Finding

| ID／等級 | 依據與可重現差異 | 產品影響 | 首選修正／最低驗收 |
| :--- | :--- | :--- | :--- |
| B1／Blocking | `arch.md` §2.7／§4.6／§5.1 規定 Reasoner 於 THINK 依 pending metadata 安排 read；USER 已確認 M5 MQTT 應在下一個 eligible PERCEPTION 由 SM 強制 `read-only`。External message 若於 ACTION 到達，現行流程仍先進 listen | 多一次無意義 ASR 等待；external reply 延遲且 prompt source 不再單一，產品行為取決於訊息到達時機 | 為 M5 MQTT profile 增加 SM 的 deterministic pending substitution：候選為 listen 且 pending 非空時改成唯一 read；不取消當前 operation、不混 listen/read。驗收 ACTION 期間到達 result 後下一 perception 只有 read |

## 3. 建議可直接採用的架構文字

### §2.7／§4.8 — profile-specific pending policy

通用 Reasoner 仍可觀察 payload-free pending metadata並產生 `next_perceptions`。M5 MQTT profile
採更窄的 deterministic policy：Reasoner 維持正常 continuing route 與 listen 候選；SM 在
PERCEPTION Entry 前以 opaque pending IDs 判斷是否把該 listen 候選替換成單一 read。SM 不讀
payload、不把 external text 插入當前 THINK，也不改寫 `LLMResponse`。

### §4.5／§4.6 — eligible PERCEPTION boundary

External message 不取消或搶占已在執行的 PERCEPTION、THINK、ACTION、tool_feedback、Speak 或
Conversation replacement。當 current operation 已完成且 continuing route 即將進入下一
PERCEPTION 時，SM 先依既有 route／status 得到候選 perception：

1. M5 MQTT profile 的候選恰為 `(listen,)` 且該 session 有 pending IDs時，原子選定
   `(read,)`；本 turn 不啟動 listen。
2. 選定 read 後沿用既有 `begin_read()` → read task 順序；多則訊息依 Ch 7 arrival order
   由同一 read window 消費。
3. 邊界選定後才到達的訊息依既有 Signal 線性化結果留作 pending，等下一個 eligible 邊界。
4. 已選定／執行的 Look 不被 external message 取消；M5 既有 read／Look 不交錯邊界維持，pending
   留到 Look flow 完成後第一個 listen 候選再替換。

IDLE 的 external-message wake 仍直接以 read-only 作首輪 perception。Current turn 已選 read 時
到達的訊息仍依 Ch 7 active-window規則 assign；window close 後到達者留 pending。

### §5.1 — ownership 與回答

M5 MQTT 的 read turn只產生 external-message `PerceptionResult`，下一次 THINK 不同時接收 listen。
Application result／notification 只能在 read 後進模型；不回寫舊 `ActionCompleted`。不新增
「我收到一個訊息，請稍等」的固定 Speak phase；read→THINK 的單次回答直接標示來源並轉告內容。

## 4. 最低直接驗收

1. External message 於 ACTION/tool_feedback 到達：當前 phase 正常 join；下一 PERCEPTION 只啟動 read。
2. External message 於 listen／THINK／Speak 到達：不取消當前 operation；下一個 eligible listen
   候選被 read-only 取代。
3. IDLE arrival 仍以 read wake；active read window arrival 依既有 assign／pending 線性化。
4. 無 pending 時既有 listen、tool feedback、Look 行為不變；Look 執行中不混入 read。
5. SM 與 Reasoner 只看 opaque pending IDs；payload 仍只由 read consumer取得。

## 5. Owner 回覆位置

### Disposition

* **B1（Blocking）**：**Accepted / Revised**。已依最小 authority delta 更新 [`docs/arch.md`](../../arch.md) §2.7、§4.5、§4.6、§4.8、§5.1。

### 修改章節與採用文字摘要

1. **[`arch.md` §2.7](../../arch.md#27-cognition--認知層)**：
   * 保留通用 Reasoner 可觀察 payload-free pending metadata（opaque ID 或 count）並決定 `next_perceptions` 的契約。
   * 明定 **M5 MQTT profile** 採更窄的 deterministic policy：Reasoner 維持正常 continuing route 與 `(listen,)` 候選（read turn 只允許選擇 `speak` / `end` 並映射為 `speak` / `rest` route，不選 `tool` / `look`）；SM 在進入 PERCEPTION Entry 前以本 session 的 opaque pending IDs 判斷是否把 `(listen,)` 候選替換成單一 `(read,)`。SM 與 Reasoner 皆不讀 payload、不把 external text 插入當前 THINK，也不改寫已產出的 `LLMResponse`。
2. **[`arch.md` §4.5](../../arch.md#45-狀態轉移表) 與 [§4.6](../../arch.md#46-影響資源與資料-ownership-的-entryexit-動作)**：
   * `ExternalMessageArrived` 在非 `IDLE`（`ERROR` 與終止流程除外）不取消、不搶占已在執行的 PERCEPTION、THINK、ACTION（含 primary、`tool_feedback`、rest）、Speak 或 Conversation replacement。
   * 當 continuing route（`KEEP_NEXT`、`tool_feedback` 完成後、或 `REPLACE_NEXT` barrier 完成後）進入 `PERCEPTION Entry` 時，SM 先依既有 route / action status 得到候選組合（normalized `next_perceptions` 或 `default_perceptions`），再套用 M5 MQTT pending 替換規則：
     1. 候選恰為 `(listen,)` 且該 session 有 opaque pending IDs 時，原子選定 `(read,)`，本 turn 不啟動 `listen`。
     2. 選定 `(read,)` 後沿用既有開啟 read 消費視窗（如 `begin_read()`）→ 啟動 `read` worker task 順序；多則 pending 訊息依 arrival order 由同一 read window 消費。
     3. 邊界選定後才到達的訊息依既有 Signal 線性化結果處理：當前 turn 已選 `read` 且視窗仍開啟者依 active-window 規則 assign，視窗關閉後或非 `read` turn 到達者留作 pending，等下一個 eligible PERCEPTION 邊界。
     4. 已選定／執行的 `look` 不被 external message 取消；維持 M5 read / Look 不交錯邊界，pending 留到 Look flow 完成後第一個 `(listen,)` 候選邊界再替換。
3. **[`arch.md` §4.8](../../arch.md#48-post_action_routenext_perceptions-與-default_perceptions)**：
   * 新增 `M5 MQTT deterministic pending policy` 條目，固定 continuing route 下 `(listen,) -> (read,)` 的 SM 確定性替換規則與 Look 不交錯邊界。
4. **[`arch.md` §5.1](../../arch.md#51-外部訊息-buffer-與-read-perception)**：
   * 明確區分 `IDLE` read-only wake、active read window assign、以及視窗關閉或非 `read` operation 期間入 `pending`。
   * 明定 M5 MQTT 的 application result／notification 只能在 `read` 完成並產出 external-message `PerceptionResult` 後進入下一次 THINK，下一次 THINK 不同時接收 `listen`；不回寫舊 `ActionCompleted`，也不新增「我收到一個訊息，請稍等」的固定 Speak phase，`read -> THINK` 的單次回答直接標示來源並轉告內容。

### 未變 Invariants

* `external_message` 仍為 buffer 與 payload 唯一擁有者；SM 與 Reasoner 只看 opaque pending IDs / metadata，payload 僅由 `read` consumer 讀取。
* `IDLE` 收到 `ExternalMessageArrived` 仍直接以 `(read,)` 作為首輪 perception；active read window 內到達訊息仍依 arrival order assign，window close 後留作 pending。
* Current operation（PERCEPTION / THINK / ACTION primary / `tool_feedback` / rest / Conversation replacement）不被外部訊息打斷或取消；既有收斂、cancel 分級（§6.4 / §6.5）與 Conversation 生命週期（§4.1）不變。
* 無 pending 時既有 `listen`、`tool_feedback`、`look` 行為與 M5 read / Look 不交錯邊界維持不變。

### Next Owner

* **Designer**：核對 `AR_impl_M5_MQTT_I` 修訂內容並結案（`Resolved`），更新 `docs/status/current.md` 後繼續 M5 MQTT external wrapper native POC。

### Designer 結案

Designer 已核對 `arch.md` §2.7、§4.5、§4.6、§4.8、§5.1：B1 的 deterministic
`(listen,) -> (read,)` substitution、current-operation non-preemption、active-window 線性化、
Look 不交錯與單次 read→THINK 回答均與 USER 決策及 M5 MQTT 設計一致。B1 **Resolved**；
未新增其他 finding。下一步回到 Designer 精簡 Test Spec 輸入並執行 external wrapper native POC。
