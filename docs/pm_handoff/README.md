# PM Handoff Index

本目錄只保留目前仍具約束力的規範與待處理 handoff；已完成且後續責任已由
新文件承接的 transaction record 移至 `history/`。歸檔不代表刪除決策或證據，
引用仍須指向可追溯的歷史文件。

最後更新：2026-08-15

## Authoritative POC Documents

- [Audio POC 最終繳交清單](audio_poc_delivery_checklist.md)
- [Audio POC 團隊開發指引](audio_poc_development_guide.md)
- [Core Audio M3 要求](core_audio_m3_requirements.md)

以上文件是持續有效的規範，不因單一 handoff 完成而歸檔。

## Active Handoffs

| Delivery | 狀態 | POC disposition |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-004](DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) | `ACCEPTED — M3 AUDIO REAL PACKAGE MAY START` | Core 已正式核准 P4 Option A 選型基準（`pyalsaaudio 0.11.0` + `samplerate 0.2.4 sinc_best` + channel 0 / signed 24-bit decode + 20ms framing），解除 M3 Audio real backend 與 M4a Gate 0 阻擋。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001](DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | `ACTIVE — GATE 0 PASSED / PENDING GATE 1 CANDIDATES` | Gate 0（M3 P4 final selection）已獲 Core ACK-004 通過；待 POC 提交 ASR/TTS 候選清單申請 Gate 1 授權。 |

P4 驗證已推進最終繳交清單第 5 節「Raspberry Pi 5 與 M3 HAL 驗證」，並正式關閉 M4a Gate 0。milestone 狀態仍以 `docs/milestone/README.md` 為準。

## History

| Delivery | 歸檔理由 | 後續承接 |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-ACK-001](history/DELIVERY-AUDIO-POC-M3-ACK-001.md) | 初始 M3 contract acceptance 已完成；P1/P2 已有 evidence 與後續決定。 | P1/Option A 決定見歷史 `ACK-002`；P4 由歷史 `VALIDATION-001` 與 `ACK-004` 承接，P3 由 `core_audio_m3_requirements.md` 約束。 |
| [DELIVERY-AUDIO-POC-M3-ACK-002](history/DELIVERY-AUDIO-POC-M3-ACK-002.md) | Option A 責任邊界與可觀察結果的方向決定已完成。 | P4 implementation validation 由歷史 `VALIDATION-001` 執行，並由 active `DELIVERY-AUDIO-POC-M3-P4-ACK-004` 正式核准。 |
| [DELIVERY-AUDIO-POC-M3-VALIDATION-001](history/DELIVERY-AUDIO-POC-M3-VALIDATION-001.md) | Option A 實作驗證要求已由 POC 完整回交（A01~A10 PASS + Manifest + 決策表）。 | 由 active [DELIVERY-AUDIO-POC-M3-P4-ACK-004](DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 正式核准結案。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-003](history/DELIVERY-AUDIO-POC-M3-P4-ACK-003.md) | 中介收件確認（receipt disposition），指出缺件之 Blocking Finding。 | 已由正式核准的 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 取代。 |
| [RESP-AUDIO-M3-P4-REPRO-002](history/RESP-AUDIO-M3-P4-REPRO-002.md) | Core 核准 A10 clean-Pi rerun Option 2 之回覆。 | 已由 `CR-AUDIO-M3-P4-REPRO-002` 與 `P4-A10-RERUN-002` 執行並通過驗證。 |

只有在決定已完成、未結責任已明確轉載到 active 文件，且 repo 內引用已更新後，
handoff 才可移入 `history/`。
