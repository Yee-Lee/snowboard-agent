# PM Handoff Index

本目錄只保留目前仍具約束力的規範與待處理 handoff；已完成且後續責任已由
新文件承接的 transaction record 移至 `history/`。歸檔不代表刪除決策或證據，
引用仍須指向可追溯的歷史文件。

最後更新：2026-08-14

## Authoritative POC Documents

- [Audio POC 最終繳交清單](audio_poc_delivery_checklist.md)
- [Audio POC 團隊開發指引](audio_poc_development_guide.md)
- [Core Audio M3 要求](core_audio_m3_requirements.md)

以上文件是持續有效的規範，不因單一 handoff 完成而歸檔。

## Active Handoffs

| Delivery | 狀態 | POC disposition |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-VALIDATION-001](DELIVERY-AUDIO-POC-M3-VALIDATION-001.md) | `POC ACTION REQUIRED — COMPLETE RETURN PACKET BLOCKS FINAL ACK` | Core 已 receipt P4 summaries；POC 尚須交付 manifest-bound validation return、raw retention paths 與七項 decision table。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001](DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | `READY FOR PM RELAY — PENDING POC INTAKE SHA` | 已收到但 Gate 0 仍受 M3 P4 final selection ACK 阻擋；不授權啟動 M2–M4 候選或驗證工作。 |

P4 是目前 M1 change-request closure 與 Core Audio real-backend 的 blocking
handoff。它推進最終繳交清單第 5 節「Raspberry Pi 5 與 M3 HAL 驗證」，但不表示
POC 已獲准進入 M3。M4a contract 的收件亦不改變進場順序；milestone 狀態仍以
`docs/milestone/README.md` 為準。

## History

| Delivery | 歸檔理由 | 後續承接 |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-ACK-001](history/DELIVERY-AUDIO-POC-M3-ACK-001.md) | 初始 M3 contract acceptance 已完成；P1/P2 已有 evidence 與後續決定。 | P1/Option A 決定見歷史 `ACK-002`；P4 由 active `VALIDATION-001` 承接，P3 由 `core_audio_m3_requirements.md` 約束。 |
| [DELIVERY-AUDIO-POC-M3-ACK-002](history/DELIVERY-AUDIO-POC-M3-ACK-002.md) | Option A 責任邊界與可觀察結果的方向決定已完成。 | P4 implementation validation、完整 SHA 與 Core final selection ACK 由 active `VALIDATION-001` 承接；P3 輸出契約由 `core_audio_m3_requirements.md` 持續約束。 |

只有在決定已完成、未結責任已明確轉載到 active 文件，且 repo 內引用已更新後，
handoff 才可移入 `history/`。
