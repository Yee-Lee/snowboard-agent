# PM Handoff Index

本目錄只保留目前仍具約束力的規範與待處理 handoff；已完成且後續責任已由
新文件承接的 transaction record 移至 `history/`。歸檔不代表刪除決策或證據，
引用仍須指向可追溯的歷史文件。

最後更新：2026-08-23

## Authoritative POC Specifications

永久生效之全域開發手冊、架構契約與最終驗收清單已移至專屬規範目錄：
👉 [**`docs/specs/`**](../specs/README.md)

- [Audio POC 最終繳交清單](../specs/audio_poc_delivery_checklist.md)
- [Audio POC 團隊開發指引](../specs/audio_poc_development_guide.md)
- [Core Audio M3 要求](../specs/core_audio_m3_requirements.md)

## Active Handoffs

| Delivery | 狀態 | POC 回覆 / 下一步 |
| --- | --- | --- |
| [VAD execution scope change request](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md) | `USER AUTHORIZATION RECORDED / CORE ACK PENDING` | User 已選定 WebRTC 2.0.10 primary、Silero 6.2.1 conditional fallback；faster-whisper bundled Silero 僅為 diagnostic context。Core 須在任何 real result 前 ACK exact rows/profile 並凍結 aggregate recall gate。見 [`RESP-AUDIO-M4A-G1B-VAD-SCOPE-001`](../../poc_audio/deliveries/RESP-AUDIO-M4A-G1B-VAD-SCOPE-001.md)。 |
| [Audio POC A / B 分組觀察計畫](Audio_POC_AB_experiement.md) | `RESPONSE READY / DATA PACKET COMPLETE` | 40-record sanitized data、A/B/A+B summary、paired outcomes、README 與 reproduction command 已提交；無新 inference，不改 frozen scorecard。見 [`RESP-AUDIO-M2A-AB-SPLIT-001`](../../poc_audio/deliveries/RESP-AUDIO-M2A-AB-SPLIT-001.md)。 |
| [DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003](DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003.md) | `ACCEPTED / M2A COMPLETE / M2B GATE REVIEW` | M2B 已提出 base Q8 primary、small Q8 fallback、exact prompt recipe 與 bounded C scorecard；ASR matrix 已停止，等待 Core/User comparative review。VAD User strategy 已記錄，Core ACK 與 recall gate 仍待補齊。 |
| [POC-AUDIO-PERF-2026-001](POC-AUDIO-PERF-2026-001/feedback.md) | `CLOSED / EVIDENCE PRESERVED` | bounded/native Q8 調查已完成；結果維持原 diagnostic disposition。後續 ASR 比較由 ACK-003 的共同 M2A packet 承接。回覆見 [`RESP-POC-AUDIO-PERF-2026-001`](../../poc_audio/deliveries/RESP-POC-AUDIO-PERF-2026-001.md)。 |
| [commit_workflow_update](commit_workflow_update.md) | `INTEGRATED` | 已將 unpublished WIP squash、Candidate SHA append-only、單一 `audio` branch 與 immutable milestone tags 整合至 [`docs/audio_poc_workflow.md`](../audio_poc_workflow.md) 與 `AGENTS.md`。 |
| [DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002](DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002.md) | `SUPERSEDED IN PART / EVIDENCE PRESERVED` | Exact source、artifact/build evidence 與 tested SHAs 保留；conditional Q5 trigger、ASR execution order 與 quality/performance elimination gates 已由 ACK-003 取代。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001](DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | `GATE 1 ACCEPTED / M2A-M2B SCOPE ACKED` | Gate 1 歷史 planning/proposal 保留；ASR comparative funnel 由 ACK-003 承接。VAD 仍由 [`CR-AUDIO-M4A-G1B-VAD-SCOPE-001`](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md) 追蹤。 |

## History

| Delivery | 歸檔理由 | 後續承接 |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-ACK-001](history/DELIVERY-AUDIO-POC-M3-ACK-001.md) | 初始 M3 contract acceptance 已完成；P1/P2 已有 evidence 與後續決定。 | P1/Option A 決定見歷史 `ACK-002`；P4 由歷史 `VALIDATION-001` 與 `ACK-004` 承接，P3 由 `core_audio_m3_requirements.md` 約束。 |
| [DELIVERY-AUDIO-POC-M3-ACK-002](history/DELIVERY-AUDIO-POC-M3-ACK-002.md) | Option A 責任邊界與可觀察結果的方向決定已完成。 | P4 implementation validation 由歷史 `VALIDATION-001` 執行，並由歷史 `DELIVERY-AUDIO-POC-M3-P4-ACK-004` 正式核准。 |
| [DELIVERY-AUDIO-POC-M3-VALIDATION-001](history/DELIVERY-AUDIO-POC-M3-VALIDATION-001.md) | Option A 實作驗證要求已由 POC 完整回交（A01~A10 PASS + Manifest + 決策表）。 | 由歷史 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 正式核准結案。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-003](history/DELIVERY-AUDIO-POC-M3-P4-ACK-003.md) | 中介收件確認（receipt disposition），指出缺件之 Blocking Finding。 | 已由正式核准的 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 取代。 |
| [RESP-AUDIO-M3-P4-REPRO-002](history/RESP-AUDIO-M3-P4-REPRO-002.md) | Core 核准 A10 clean-Pi rerun Option 2 之回覆。 | 已由 `CR-AUDIO-M3-P4-REPRO-002` 與 `P4-A10-RERUN-002` 執行並通過驗證。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) | Core 已正式核准 P4 Option A 選型基準（`pyalsaaudio 0.11.0` + `samplerate 0.2.4 sinc_best`），M4a Gate 0 正式通過。 | 由已凍結之 M1 共同測試基線與 M3 real hardware integration 承接。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001 (initial revision)](history/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | 初版在 Gate 0 關閉後曾歸檔；2026-08-17 修訂版已重新成為 active handoff。 | 以 active contract 與 `RESP-AUDIO-M4A-GATE-PLAN-001` 為本輪決策來源。 |

只有在決定已完成、未結責任已明確轉載到 active 文件，且 repo 內引用已更新後，
handoff 才可移入 `history/`。
