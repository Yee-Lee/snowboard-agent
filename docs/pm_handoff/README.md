# PM Handoff Index

本目錄只保留目前仍具約束力的規範與待處理 handoff；已完成且後續責任已由
新文件承接的 transaction record 移至 `history/`。歸檔不代表刪除決策或證據，
引用仍須指向可追溯的歷史文件。

最後更新：2026-08-15

## Authoritative POC Specifications

永久生效之全域開發手冊、架構契約與最終驗收清單已移至專屬規範目錄：
👉 [**`docs/specs/`**](../specs/README.md)

- [Audio POC 最終繳交清單](../specs/audio_poc_delivery_checklist.md)
- [Audio POC 團隊開發指引](../specs/audio_poc_development_guide.md)
- [Core Audio M3 要求](../specs/core_audio_m3_requirements.md)

## Active Handoffs

當前無待處理之 blocking handoff。M1 已全數結案凍結；待進入 M2 Gate 1 提出候選評測清單時新增 handoff。

## History

| Delivery | 歸檔理由 | 後續承接 |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-ACK-001](history/DELIVERY-AUDIO-POC-M3-ACK-001.md) | 初始 M3 contract acceptance 已完成；P1/P2 已有 evidence 與後續決定。 | P1/Option A 決定見歷史 `ACK-002`；P4 由歷史 `VALIDATION-001` 與 `ACK-004` 承接，P3 由 `core_audio_m3_requirements.md` 約束。 |
| [DELIVERY-AUDIO-POC-M3-ACK-002](history/DELIVERY-AUDIO-POC-M3-ACK-002.md) | Option A 責任邊界與可觀察結果的方向決定已完成。 | P4 implementation validation 由歷史 `VALIDATION-001` 執行，並由歷史 `DELIVERY-AUDIO-POC-M3-P4-ACK-004` 正式核准。 |
| [DELIVERY-AUDIO-POC-M3-VALIDATION-001](history/DELIVERY-AUDIO-POC-M3-VALIDATION-001.md) | Option A 實作驗證要求已由 POC 完整回交（A01~A10 PASS + Manifest + 決策表）。 | 由歷史 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 正式核准結案。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-003](history/DELIVERY-AUDIO-POC-M3-P4-ACK-003.md) | 中介收件確認（receipt disposition），指出缺件之 Blocking Finding。 | 已由正式核准的 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 取代。 |
| [RESP-AUDIO-M3-P4-REPRO-002](history/RESP-AUDIO-M3-P4-REPRO-002.md) | Core 核准 A10 clean-Pi rerun Option 2 之回覆。 | 已由 `CR-AUDIO-M3-P4-REPRO-002` 與 `P4-A10-RERUN-002` 執行並通過驗證。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) | Core 已正式核准 P4 Option A 選型基準（`pyalsaaudio 0.11.0` + `samplerate 0.2.4 sinc_best`），M4a Gate 0 正式通過。 | 由已凍結之 M1 共同測試基線與 M3 real hardware integration 承接。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001](history/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | M4a Contract 階段 0 已由 ACK-004 關閉，後續各階段評測規則已移入 M2/M3/M4 milestone 及 specs。 | 由 `docs/milestone/` 各 milestone 流程承接。 |

只有在決定已完成、未結責任已明確轉載到 active 文件，且 repo 內引用已更新後，
handoff 才可移入 `history/`。
