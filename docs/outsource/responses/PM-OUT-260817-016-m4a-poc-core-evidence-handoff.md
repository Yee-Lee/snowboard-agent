# Response: PM-OUT-260817-016 — M4a POC / Core Evidence Handoff

- **Handoff**: `PM-OUT-260817-016-m4a-poc-core-evidence-handoff`
- **Findings**: `OUT-M4A-2026-002` ～ `OUT-M4A-2026-005`
- **Status**: `Core revision ready — Audio POC committed Gate plan pending`
- **Response owner**: Core Team Designer
- **Date**: 2026-08-17
- **Reviewed Core baseline**: `dev_agent_m3` / `c559e5cf65d20676696293f06f1e5bc2afd02ae6`
- **Reviewed Audio POC baseline**: `dev_audio_m2` / `aad41ce13333bdf94bf6d6ab0996f83982f9f0b1`
- **Audio POC revised-plan SHA**: `Pending; current reviewed SHA predates this revision`
- **Core response SHA**: `Pending PM intake after this response is committed; this file does not self-reference its future commit`
- **Architecture change**: `No`

## 1. 結論與交付

Core已修訂既有權威contract [`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../deliveries/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)、[`M4.md`](../../milestones/M4.md)及[`milestone_progress.md`](../../reviews/milestone_progress.md)，沒有建立重複delivery addendum。User應將contract revision交付Audio POC Team；POC依contract §10在自己的repo提交authoritative Gate plan / reply，再回傳path、branch與完整40-character SHA。

已核對Audio POC目前為乾淨的`dev_audio_m2` / `aad41ce13333bdf94bf6d6ab0996f83982f9f0b1`，與handoff reviewed baseline一致。此SHA可作comparison baseline，但尚未包含本revision要求的Gate 2可執行計畫，因此不能填作`OUT-M4A-2026-005`的完成證據。

## 2. Findings disposition

| Finding | 裁決 | 權威定位 | Audio POC / Core影響 |
| :--- | :--- | :--- | :--- |
| `OUT-M4A-2026-002` | **Resolved in Core contract; POC handoff pending** | Contract §4、§8～§10；M4 §6.2/§6.2.1 | Gate 2A qualification只放行不鎖artifact的adapter scaffold；Gate 2B須完成Audio internal M4、review、`POC Accepted` final handoff與kit。若2B發現blocker，scaffold可在契約不變時續行，但baseline lock / acceptance停止 |
| `OUT-M4A-2026-003` | **Resolved in Core contract** | Contract §7.1 | P1～P12及internal M4已分類為inherited、reused/rerun或product-only。Core Gate 3必填POC handoff / SHA / evidence / fixture checksum、product SHA、inheritance理由與delta Test ID / result |
| `OUT-M4A-2026-004` | **Resolved in Core contract** | Contract §7.2 | Final handoff須含provenance、protocol/schema、fixture/checksum、validator、lifecycle/failure/cleanup、offline、resource、20 sessions、risk與index；raw audio、model、wheel、`.so`及benchmark orchestration不得直接進Core Git |
| `OUT-M4A-2026-005` | **Core dependency/review rules resolved; POC executable plan pending** | Contract §8～§10 | External Gate 1 / 2A / 2B已映射Audio M1～M4與P1～P12。POC須在自己的repo補齊owner、dependency、platform、fixture、runner、evidence、decision、cleanup與exact-SHA cut point，commit後才可進Gate 1 review |

## 3. Evidence inheritance / product-delta裁決

Core不重跑候選比較，也不重新定義Accepted POC SHA中已凍結的candidate identity、artifact checksum、license、quality comparison、rejected reasons與fixture / metric。下列風險不能繼承為產品Pass，必須在Core product exact SHA重驗：

- adapter與M3 HAL wiring、AudioInput / ASR及TTS / AudioOutput格式；
- production config、dependency / model / voice lock、packaging與受控artifact取得；
- Resource Manager / State Machine lifecycle、cancel / abort / reopen / cleanup；
- VAD→ASR→Reasoner→TTS composition、實際產品process-tree resource與offline；
- 產品exact-SHA regression及Tester acceptance。

Audio POC提供的validators、small non-sensitive vectors、schema、assertions與sanitized expected result可作portable conformance kit。Core若不沿用某項可重用資產，須在Gate 3 mapping說明差異及替代測試，不要求POC代寫Core private implementation。

## 4. 無循環的M4a / M4b順序

Audio POC Gate 2B使用Core核准、versioned deterministic Reasoner / LLM residency surrogate完成20-session、failure及offline internal M4，無須等待LLM final winner。Audio `POC Accepted` package完成後交Core intake，再供LLM POC Gate 2B做實際P9 / P10B combined validation。最後Core在兩個Accepted POC input齊備後做production composition驗收。Surrogate只保留M4b資源envelope，不等於combined product Pass。

## 5. Audio POC repo comparison與必改範圍

已核對baseline中的權威規劃：

- `docs/milestone/README.md`
- `docs/milestone/m1_frozen_gates_draft.md`
- `docs/milestone/m2_candidate_evaluation.md`
- `docs/milestone/m3_real_hardware_integration.md`
- `docs/milestone/m4_combined_validation_and_delivery.md`
- `docs/poc/poc_audio_m4_audio_poc_plan.md`
- `docs/pm_handoff/history/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md`

POC可在這些既有文件中選定單一authoritative plan，不需複製Core contract；但每個P1～P12必須可定位producer / owner、prerequisite、platform、fixture、command / runner、output / evidence、decision rule、cleanup及exact-SHA binding，並加入External Gate 1 / 2A / 2B crosswalk與final handoff / kit cut point。

## 6. Architecture與尚未決事項

**Architecture change: No.** 本revision不改process owner、IPC、HAL public API或ASR / TTS ownership，只固定POC evidence到既有Core產品架構的交接規則。因此不修訂`docs/arch.md`。`docs/model_spec.md`須等Gate 2B final reference identity成立後再固定engine / model / voice / provenance，不預填尚未選出的baseline。

Gate 1仍待Core書面裁決候選eligibility與User / PM產品門檻，包括語言範圍、ASR quality threshold及TTS review threshold；POC應在proposal中列為`Core decision required`，不可自行默認Pass。

## 7. Audio POC回覆驗收

Audio POC Team應提交單一reviewable commit，並由回覆訊息提供：

1. authoritative Gate plan / reply path、branch、完整40-character commit SHA；
2. External Gate 1 / 2A / 2B→Audio M1～M4→P1～P12→evidence唯一crosswalk；
3. 逐work-package owner、dependency、estimate / re-estimation trigger、entry / exit、platform、runner、evidence、cleanup與failure / no-go；
4. M4b surrogate ID / version / resource envelope及未來Accepted LLM package的處理規則；
5. final handoff ID、Accepted POC SHA與kit structure的產生時點；正式值只能在相應commit完成後回報，不得預填未來SHA。

收到上述committed outcome前，`OUT-M4A-2026-005`維持`POC response pending`，Gate 1不視為已核准，真實candidate下載、build與benchmark不得開始。

## 8. Core本輪驗證

- 比對Audio POC branch / HEAD與handoff reviewed baseline一致，且工作目錄乾淨。
- 逐項檢查Gate 2A / 2B / Gate 3 entry、exit、owner、阻擋及change-request回流。
- 對P1～P12與Audio internal M4完成inheritance / delta及portable-kit mapping。
- 僅修改文件；未執行或宣稱Audio POC benchmark / Pi evidence Pass。
