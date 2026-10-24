---
requestor: Designer
owner: Architect
status: Revised
activation: Deferred until M4B-MVA-EFFICIENCY returns and Designer selects one adoption proposal
---

# AR_impl_M4B_II — prospective efficiency and lifecycle contract

This is a prepared focused review request, not an active request to review both POC candidates.
After the POC result, Designer replaces candidate branches with one selected adoption proposal, then
activates review of [002 design](../implement/m4b_mva_002_decisions.md) and [M4C](../milestones/M4C.md).
The User requested POC task delivery and remaining design/planning. The POC experiment is independently
authorized to test candidates, not authority to change production architecture.

Affected decisions: an unclaimed clean Conversation before SM begin versus current THINK-owned open;
incremental semantic text inside one Reasoner-owned speak operation versus current one-final-response
dispatch; basic preparing/error display versus boot Blank; explicit launcher ownership/restart lifecycle.
Recommended resolution: preserve SM session identity, adapter single ownership, Reasoner action authority
and RM recovery; bind pre-open atomically, reject late completions; retain a full-response consumer in M4B,
add bounded streaming consumer in M4C; startup launcher stays external to App.

Architect updates only affected authority clauses and returns disposition; Reviewer then reviews the
corresponding design/plan delta. Do not reopen model selection, unchanged Audio qualification or 001
history. Until approval and POC adoption, no production implementation authorization.

---

## Architect 回應（2026-09-06，含 AR_review_M4B_I 修正）

依 AR_impl_M4B_II 四個 affected decisions 修訂 arch.md。初版經 AR_review_M4B_I 指出四項 Blocking（互斥時序、streaming 架構路徑、display 唯一觸發源、唯一退出路徑），均已採用 Reviewer 首選文字修正。

**Decision 1 — Conversation ownership / pre-open**

* **§4.1**：區分 unclaimed clean prepared object 與已綁定 session 的 Conversation；SM begin 原子綁定或按需建立；component owner/API 屬 implement。
* **§4.6 THINK Entry**：「原子綁定相容 prepared object，或按需建立；取得完成前不得 generate」。
* **§4.6 ACTION Exit / ERROR Entry / §4.7**：各路統一為單次收斂順序——end-intent → active convergence (依 §6.5 一次收斂全部 in-flight) → terminal/join proof → Conversation close → clear tracking/accept new session。Shutdown 先進 shutdown mode 拒絕新 wake 再收斂。
* **不變**：SM 仍是 session identity 唯一擁有者。

**Decision 2 — Incremental semantic text（streaming speak）**

* **§2.8**：M4C streaming-speak control 綁定 `(session_id, turn_id, correlation_id)`，SM 在 THINK 授權啟動唯一 speak worker；fragment 為 operation 內資料；delivery/playback stage 先完成只記 private notice，speak worker 維持 in-flight 不 return，進 ACTION 且 terminal 驗證通過後才發布 `ActionCompleted`；terminal `LLMResponse` 仍是唯一 cognition Fact。M4B 不啟用。
* **§4.5**：THINK→ACTION 行備註 delivery/playback stage private notice 不提前轉移。
* **§4.6 ACTION Entry**：已啟動則沿用既有 worker，否則依 `LLMResponse` 啟動。

**Decision 3 — Preparing / error display**

* **§4.3**：三個資料來源（`StateChanged` / lifecycle client / error observer）；`display_spec.md` 為畫面/時機/文案權威；架構不新增 SM state；M4C preparing 須先修訂 display spec。

**Decision 4 — Launcher ownership / restart lifecycle**

* **§5.4**：graceful exit（`ShutdownRequested`）與 Level 3 fatal termination 並存；SM/RM 不 self-restart；external = process ownership 邊界，不免除產品交付。

狀態維持 `Revised`，等待 Reviewer 複審通過後再由 Designer（Requestor）審核。
