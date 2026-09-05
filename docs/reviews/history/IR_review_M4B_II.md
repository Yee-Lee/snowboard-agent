---
requestor: "Reviewer"
owner: "Designer"
status: "Resolved"
---

# IR_review_M4B_II — M4B-MVA 三面審查（Step 2）

日期：2026-09-05。依 M4B_MVA.md Step 2，同一輪審查三面向。

## Scope

1. Architect 修訂 arch.md（回應 AR_impl_M4B_I）
2. Designer 設計 ch_m4b_llm_production.md
3. POC 量測計畫 REQUEST-LLM-POC-M4B-MVA-MEASURE-001

## Conclusion: PASS — 0 Blocking, 3 Advisory

### Surface 1: arch.md amendments — PASS

Architect 六點修訂（§2.7 M4 Reasoner 分工 / P5 分界、§4.1 Session 內 Conversation、
§4.6 THINK Entry session begin、§4.6 ACTION Exit + ERROR Entry session end、
§4.7 三事件表四路收斂、§8.3 記憶範圍）逐項與 AR_impl_M4B_I 要求對齊。
不變項（empty rest / LLMResponse 三欄 / SM 唯一 session owner / RM 唯一 rebuild owner /
startup-static capability / no-network）均未異動。無矛盾、無遺漏。

AR_impl_M4B_I 可由 Requestor（Designer）標記 Resolved 並歸檔。

### Surface 2: ch_m4b_llm_production.md — PASS

text/end 2-field schema、Reasoner 獨立 action/next_perceptions、ReasonerSessionControl
begin/end、四路 finish_convergence、P5 pre-inference vs dirty 分界、capacity-driven
replacement、validation ownership 四層、performance endpoints 五層、profile register
與 POC handoff 均與 arch.md 對齊。無矛盾、無遺漏。

- Advisory-1：§3 begin_session 觸發點描述（WAKE 前 vs THINK Entry）可在定版時一句話釐清。
- Advisory-2：§7 profile 表格可補齊「未凍結不得驗收」保護句（§4 已涵蓋）。

### Surface 3: REQUEST-LLM-POC-M4B-MVA-MEASURE-001 — PASS

parity（硬體/runtime/schema/lifecycle/prompt）、單一自變量比較（prewarm none vs once）、
cold boot/same-boot matrix、memory soak（3 cycles × 20 sessions）、recovery injection、
manual semantic rubric（12 holdout / 6-point）、E2E latency 界定（speech-end → audible onset）、
gate exit（只有 Designer 審核解除）均與設計及架構對齊。無矛盾、無遺漏。

- Advisory-3：Audio package 不可用時的量測欄位填寫規則可在定版時確認。

## Advisory disposition

三則 Advisory 均不影響 Resolved。Owner（Designer）可自行決定於定版時處理或另行記錄。

## Effect on M4B-MVA gate

Step 2 完成。Designer 可進入 Step 3（定版）。

## Designer 接件檢查（2026-09-05）

已核對 Architect 主文件 diff、AR_impl 回覆、設計及 POC 工作包。
上述 Reviewer 結論保留；本節記錄 Step 3 定版處置，不新增 Blocking 或宣告定版完成。
本單已 Resolved，依 workflow 歸檔；接件檢查當時AR_impl_M4B_I仍為Revised，待下列時序對齊後確認。

1. **Advisory-1 直接影響面：begin/end 時序。** 設計 §3 實際寫的是「WAKE 分配 ID 後、
   PERCEPTION 前」，不是 WAKE 前；arch.md §4.6 則在首 turn THINK Entry 通知 begin。
   同時 arch.md §4.6/§4.7 要求先通知 end 再收斂，設計 §3 及
   `finish_convergence` 卻在 in-flight 收斂後才呼叫 end。故「均已對齊」尚需此項釐清。
   Designer 定版首選依架構調整設計：首 THINK 先完成 ownership 登記，才允許
   open/generate；四路結束先登記非阻塞 end 控制工作、禁止新 admission，
   待 active operation 取消／完成證明後才執行 native close，close 完成才清 tracking／恢復 wake。
   CONTROL completion 納入收斂，但不可讓 end task 等待包含自己的集合。
   no-THINK 且未登記的 end 為 no-op；wrong-session end 不得關閉新 session。
   最低驗證沿設計 §9：no-THINK exit、open/generate/close 期間 interrupt/shutdown、
   late ACK；SM inbox 持續消費、cancel 後無正常 Fact、close 證明前不開新 session，
   無法證明 cleanup 則沿 Level 2/3。此項限 session 設計與直接引用，不重開模型選型或 M4A。
2. **POC 定版待辦。** 工作包 §4 明定平台 reserve／停止條件未定不得交付；目前仍未列
   具體判準，steady-window 算法／窗口也待固定。Step 3 必須補齊量測保護條件、
   案例／順序與結果欄位；這些不同於 Step 5 才產生的量測值及 Step 6 採用的產品 profile。
   Advisory-3 首選：Audio/onset 不可量時 audible latency 留 null 並記缺口原因，
   scope 限 LLM subsystem；E2E 項保持 Open，不以 TTFT、0 或推估值補成 PASS。
3. **Advisory-2 與狀態同步。** 定版時在設計 §7 就地重申 profile 未凍結不得正式驗收；
   同步設計首段／§11、POC 文件仍寫 Reviewer pending 的狀態，保留未交付與進場限制。

接件檢查當時仍為 M4B-MVA-001 draft / Step 3 pending；未交付 POC、未解除 gate。
該次為文件一致性檢查，未執行產品或 target 驗收。

## Designer Step 3 completion（2026-09-05）

三則Advisory及接件檢查的直接影響面均已處置：設計§3統一begin/end時序，§7補上
profile未凍結不得驗收；POC工作包固定512MiB runner安全線、停止條件、session 11–20
分析窗口、case順序及Audio不可量時的null/Open規則；文件狀態同步為Reviewer PASS、
Designer frozen、未交付。AR_impl_M4B_I已由Designer確認Resolved並歸檔。

Step 3完成，下一步為Designer Step 4交付。此結論不代表POC gate已Open、profile已採用、
Developer／Tester可進場或M4B產品已驗收。
