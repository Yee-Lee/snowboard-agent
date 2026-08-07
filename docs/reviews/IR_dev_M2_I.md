---
requestor: "Developer"
owner: "Designer"
status: "Revised"
---

# IR_dev_M2_I — Reasoner 無 ActionPayloadValidator 注入路徑

## Finding

### Blocking — Ch 2 constructor 與 Ch 9 shared-validator 契約無法同時落實

- 契約依據：`implement/ch02_contracts.md` §2.8 固定 `Reasoner.__init__(llm, prompt_builder, bus, capability_of)`；`implement/ch09_action_payload.md` §0 ch9-Q7、§7–§8 要求 Reasoner 與 StateManager 共用同一個 `ActionPayloadValidator` instance；`implement/ch05_resource_manager.md` §3.5 僅定義 validator 注入 SM。
- 最小重現：依 Ch 2 四參數建構 Reasoner 後，instance 只能取得 LLM、PromptBuilder、Bus、capability query，無法取得 main 建立的 validator；若 Reasoner 自建 validator，又需要同一個 sealed ToolRegistry 且違反「同一 instance」。
- 預期：存在不修改其他 owner 私有狀態、可由 composition 明確接線的 validator 注入路徑。
- 實際：只能擴充 Reasoner constructor、擴充 PromptBuilder 公開責任、讀取其他物件 private 欄位或使用 module global；四者皆未獲契約授權。
- 影響：WP-M2-07 Reasoner normalizer、WP-M2-09 composition 與 `M2-WRK-003` 無法在不私改 API 下完成。
- 建議修正方向：在 Ch 2 §2.8 的 `Reasoner.__init__` 新增明確 `action_validator: ActionPayloadValidator` 參數，並在 Ch 5 §3.5 composition 表補上同一 instance 同時注入 SM/Reasoner；或由 Designer 指定等價窄介面。
- 最低驗收：Reasoner normalizer 與 SM 對同一 payload 呼叫 object identity 相同的同步 validator，且 ToolRegistry 仍只在 startup seal 一次。

## Developer 暫行處置

WP-M2-05、06、08 與其他不依賴此裁定的工作繼續；不擴充 Reasoner public constructor，待 Owner Revised 後再實作 WP-M2-07/09。

---

## Designer 裁定（Revised）

**採納 Developer 建議修正方向。**

Finding 屬實，論據精確。`ActionPayloadValidator` 無 mutable call state（Ch 9 §7 明載），「同一 instance」語意可完全由 composition 直接注入達成，不需要任何 global / singleton 或讀取他人 private 欄位。

**修正執行（同一 commit）：**

1. **`Ch 2 §2.8`** `Reasoner.__init__` 新增第五個參數：
   ```python
   action_validator: ActionPayloadValidator,  # Ch 9 §7；與 SM 共用同一 instance
   ```
   並在「依賴注入」段補充說明，包含此參數解決 IR_dev_M2_I 的溯源。

2. **`Ch 5 §3.5`** 在 A 類早依賴段落的結尾補充：
   > 同一個 `ActionPayloadValidator` instance 在組裝時亦直接傳入 Reasoner constructor（Ch 2 §2.8 `action_validator` 參數），確保 Reasoner normalizer 與 SM THINK Exit 呼叫同一 instance 以符合 ch9-Q7 契約；此 instance 無 mutable call state，不構成 ownership 問題。

**未修改範圍：**
- Ch 9 §7 `ActionPayloadValidator` 定義不變（本章是 validator 的 owner）。
- Ch 9 ch9-Q7 結論「共用同一 instance」語意不變，只補齊注入路徑。
- ToolRegistry seal 時序不變（Reasoner start 前完成）。
- SM constructor 簽名不變。
- 無 architecture change（不修改 arch.md）。

**最低驗收條件（供 Developer 驗收 WP-M2-07/09 參考）：**
- `M2-WRK-003` 對應測試可用注入同一 `ActionPayloadValidator` instance 驗證 Reasoner normalizer 與 SM THINK Exit 結果一致，且不需要讀取私有欄位或建立 global。
- `ToolRegistry` 仍只在 startup seal 一次，Reasoner constructor 接收的 validator 於 seal 後建構或建構後 seal 皆可，但最遲在第一次 `reason()` 前已 sealed（Ch 9 §0 ch9-Q8）。

