# Response: PM-OUT-260817-016 — M4a POC / Core Evidence Handoff

- **Handoff**: `PM-OUT-260817-016-m4a-poc-core-evidence-handoff`
- **Findings**: `OUT-M4A-2026-002` ～ `OUT-M4A-2026-005`
- **Status**: `Resolved — G1A durable intake complete; archived`
- **Response owner**: Core Team Designer
- **Date**: 2026-08-17
- **Reviewed Core baseline**: `dev_agent_m3` / `c559e5cf65d20676696293f06f1e5bc2afd02ae6`
- **Reviewed Audio POC baseline**: `dev_audio_m2` / `aad41ce13333bdf94bf6d6ab0996f83982f9f0b1`
- **Accepted Audio POC plan**: `poc_audio/deliveries/RESP-AUDIO-M4A-GATE-PLAN-001.md` / `dev_audio_m2` / `5d4086d2ae9011c559b10012b55414a87a3a8522`
- **Initial Core response commit**: `d81601789ef40aeccd01dd8d4b9db67a01d76163`
- **Core planning ACK**: [`DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001`](../deliveries/DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001.md) / `dev_agent_m4` / `6fe09257304a2eb56723a5e8e8d4ad94d9f41963`
- **Architecture change**: `No`

## 1. 結論與交付

Core已修訂既有權威contract [`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../deliveries/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)、[`M4.md`](../../milestones/M4.md)及[`milestone_progress.md`](../../reviews/milestone_progress.md)，沒有建立重複contract addendum。Audio POC已回交authoritative Gate plan；Core接受該plan並以獨立planning ACK記錄D01～D05與Gate 1A授權邊界。

已核對Audio POC工作目錄乾淨；`origin/dev_audio_m2`目前為`756ded69dd7b4661fcbac272d4d234c387890fc8`，且包含plan commit `5d4086d2ae9011c559b10012b55414a87a3a8522`。Core relay副本與POC authoritative plan的SHA-256同為`2c186c6f777c830c984bd476e7cb8a8f6e977110875b50bce732c18e2f8d2810`；POC保存的contract也與Core revision checksum一致。Core G1A ACK已由`6fe09257304a2eb56723a5e8e8d4ad94d9f41963` durable commit，因此016兩項行政closure條件均已完成。

## 2. Findings disposition

| Finding | 裁決 | 權威定位 | Audio POC / Core影響 |
| :--- | :--- | :--- | :--- |
| `OUT-M4A-2026-002` | **Resolved** | Contract §4、§8～§10；M4 §6.2/§6.2.1；G1A ACK | Gate 1A / 1B、Gate 2A / 2B與Gate 3 crosswalk已由POC plan承接；Gate 2A只放行scaffold，Gate 2B才固定final reference。若2B發現blocker，scaffold可在contract不變時續行，但baseline lock / acceptance停止 |
| `OUT-M4A-2026-003` | **Resolved in Core contract** | Contract §7.1 | P1～P12及internal M4已分類為inherited、reused/rerun或product-only。Core Gate 3必填POC handoff / SHA / evidence / fixture checksum、product SHA、inheritance理由與delta Test ID / result |
| `OUT-M4A-2026-004` | **Resolved in Core contract** | Contract §7.2 | Final handoff須含provenance、protocol/schema、fixture/checksum、validator、lifecycle/failure/cleanup、offline、resource、20 sessions、risk與index；raw audio、model、wheel、`.so`及benchmark orchestration不得直接進Core Git |
| `OUT-M4A-2026-005` | **Resolved by accepted committed plan** | POC `RESP-AUDIO-M4A-GATE-PLAN-001` §3～§9；Contract §8～§10；G1A ACK | WP0～WP5、S0～S5與P1～P12已定位owner、dependency、platform、fixture、planned runner、evidence、decision、cleanup及SHA cut。G1A acceptance不等於candidate authorization；G1B仍須逐列ACK |

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

## 5. Audio POC committed outcome intake

POC commit `5d4086d2ae9011c559b10012b55414a87a3a8522`更新下列權威規劃並新增response：

- `docs/milestone/README.md`
- `docs/milestone/m1_test_and_audio_baseline.md`
- `docs/milestone/m2_candidate_evaluation.md`
- `docs/milestone/m3_real_hardware_integration.md`
- `docs/milestone/m4_combined_validation_and_delivery.md`
- `docs/pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md`
- `docs/pm_handoff/README.md`
- `poc_audio/deliveries/RESP-AUDIO-M4A-GATE-PLAN-001.md`

Plan已提供唯一External Gate→M1～M4→WP→P1～P12→evidence crosswalk，並明示planned runner在S0尚不存在，不把未實作command誤標為Pass。這足以關閉016的planning finding；runner實作、Gate 1B proposal與後續evidence由各自gate追蹤。

## 6. Architecture與尚未決事項

**Architecture change: No.** 本revision不改process owner、IPC、HAL public API或ASR / TTS ownership，只固定POC evidence到既有Core產品架構的交接規則。因此不修訂`docs/arch.md`。`docs/model_spec.md`須等Gate 2B final reference identity成立後再固定engine / model / voice / provenance，不預填尚未選出的baseline。

User已接受D01～D05：產品語言固定`zh-TW`；VAD可進Audio POC evaluation但仍在HAL外且不是M4a production dependency；Gate 1拆為G1A planning與G1B candidate scope；provenance-only acquisition邊界已固定；P9 surrogate由Core Designer在WP4 / S4前提供；G1A / G1B使用分開ACK。Audio POC較嚴格的frozen quality gate繼續有效。

## 7. Gate 1A acceptance與016 closure

G1A ACK接受以下已commit內容：

1. authoritative plan path、branch與完整commit SHA；
2. External Gate 1A / 1B / 2A / 2B→Audio M1～M4→WP0～WP5→P1～P12 crosswalk；
3. owner、dependency、estimate / re-estimation、entry / exit、platform、runner、evidence、cleanup、failure / no-go與S0～S5；
4. P9 surrogate prerequisite、final handoff及portable conformance kit產生規則。

016不等待G1B、candidate build或Gate 2A / 2B實測。POC remote已包含`5d4086d...`，Core G1A ACK亦已commit並直接交付，因此本handoff標記`Resolved`並歸檔。後續candidate scope由`DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`承接，不重開016 findings。

## 8. Core本輪驗證

- 解析Audio POC plan exact commit並確認工作目錄乾淨；確認`5d4086d...`可由`origin/dev_audio_m2`解析。
- 比對Core relay副本、POC authoritative response及雙方contract checksum一致。
- 逐項檢查Gate 1A / 1B / 2A / 2B / Gate 3 entry、exit、owner、阻擋及change-request回流。
- 驗證WP0～WP5、S0～S5、P1～P12、inheritance / delta及portable-kit mapping齊全。
- 僅修改文件；未執行或宣稱Audio POC benchmark / Pi evidence Pass。
