# M4後ALPHA / M7後BETA產品收斂Gate

- **Handoff ID** : `PM-OUT-260814-012-alpha-beta-product-convergence`
- **Status** : `Ready for PM`
- **Finding ID** : `OUT-ROADMAP-2026-001`
- **Related handoff** : `PM-OUT-260805-002-m3-m4-poc-planning`
- **Related POC-contract handoffs** : `PM-OUT-260814-010-m4a-audio-poc-contract-gate` 、 `PM-OUT-260814-011-m4b-llm-poc-contract-gate`
- **User decision** : `2026-08-14` ，M4後加入ALPHA產品化收斂；M7後加入BETA完整產品收斂
- **Reviewed Core candidate** : branch `dev_agent_m3` , HEAD `fb144bf4b8f530a98189feb5467546c398e96a41`

## 結論

Core目前只定義M4 ~ M7功能milestone，並以M4→M5→M6→M7串行；尚未區分功能完成與產品成熟度。請保留M4 ~ M7既有功能責任，在M4 Accepted後新增 `ALPHA` Voice-only產品化收斂gate，在M7 Accepted後新增 `BETA` 完整產品收斂gate。

此決議不阻擋目前M3開發 / 驗收，也不授權提前實作M4 ~ M7。它會成為M4 Design Ready、M5 entry與M7後產品結論的必要規劃輸入。

## 必做修訂

### `OUT-ROADMAP-2026-001` —— Blocking for M4+ roadmap Design Ready / Non-blocking for current M3

- 將權威依賴更新為：`M3 → M4 → ALPHA → M5 → M6 → M7 → BETA`。M4a / M4b可依各自Accepted POC input準備，M4c仍依賴兩者；三者同SHA通過後才是M4 Accepted。
- `ALPHA` 固定為Voice-only產品收斂：Button、Listen / ASR、Reasoner / LLM、Speak / TTS、M4c Session Display與離線操作；不得加入MQTT / external message / 實際tool、voice wake / Vision或M7正式動畫 / assets。
- `ALPHA` 須固定hardware / config / model / runtime / dependency / license / checksum，並定義可重現install / start / stop / reboot、重複session / soak、failure / recovery / shutdown、resource / thermal、privacy、manifest、known limits及完整SHA evidence。M5改為引用 `ALPHA Accepted` exact SHA。
- `BETA` 固定為M7後的全能力產品收斂：在同一Beta候選SHA重跑M4 ~ M7 regression，涵蓋M5 external message / tool、M6 wake / Vision與M7完整Display UX，以及長時間穩定、診斷、artifact / config / model / asset inventory及Beta manifest。Beta不得被寫成GA / production release的同義詞。
- 分開記錄 `M4 Accepted` 與 `ALPHA Accepted` 、 `M7 Accepted` 與 `BETA Accepted` ；不得以feature milestone通過直接推定產品成熟度gate通過。
- Core Designer定義scope與Requirement mapping；Tester在各gate Design Ready後建立test spec。若新增systemd / supervisor / deployment / persistent config / update / rollback或process ownership，須交Architect review並修訂 `docs/arch.md` ；否則delivery聲明 `Architecture change: No` 及逐項理由。

## 驗收方式

- Core在單一候選commit提交：
  - Delivery : `docs/outsource/deliveries/DELIVERY-ALPHA-BETA-ROADMAP-001.md`
  - Response : `docs/outsource/responses/OUT-ROADMAP-2026-001.md`
  - 新增ALPHA / BETA權威規劃文件，建議為 `docs/milestones/ALPHA.md` 與 `docs/milestones/BETA.md` ；若採其他路徑，response須說明唯一權威位置。
  - 同步修訂 `docs/milestone.md` 、 `docs/milestones/M4.md` 、 `M5.md` 、 `M6.md` 、 `M7.md` 與 `docs/reviews/milestone_progress.md` ，使依賴、entry / exit、排除、owner、evidence、exact-SHA規則與狀態一致。
  - 提供M4→ALPHA、ALPHA→M5、M7→BETA的Requirement / future Test ID trace；本輪只做Design Ready規劃，不提前建立Developer工作包或實作Alpha / Beta code。
- Response須列comparison baseline、完整candidate SHA、architecture-change聲明、逐項修改定位、文件檢查結果、尚待User / Designer / Architect / Tester決定的門檻及未完成事項。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄的 `decision_record.md` 或 `review_notes.md` 。Core提交後，PM拉回最新repo並以branch / 完整HEAD SHA通知Internal Designer進行intake；Agent不直接寄送、上傳或修改Core repo。
