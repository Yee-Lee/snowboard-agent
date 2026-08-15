# Audio POC Specifications & Guidelines

本目錄存放 Audio POC 生命週期中持續生效的權威規範、架構契約與最終驗收檢核清單。

## Authoritative Documents

| 文件 | 用途與說明 |
| :--- | :--- |
| [arch.md](arch.md) | **Snowboard 架構設計**：系統整體架構、貫穿性原則 P1-P5、模組邊界、資料流與介面契約。 |
| [audio_poc_delivery_checklist.md](audio_poc_delivery_checklist.md) | **Audio POC 最終繳交清單**：定義 M1 到 M4 最終驗收必須滿足的 8 大標準（Manifest、再現性、品質、Pi 5 硬體驗證、資料安全等）。 |
| [audio_poc_development_guide.md](audio_poc_development_guide.md) | **Audio POC 團隊開發指引**：規範 POC 各階段目標、最小 Adapter 契約、第一輪候選與必測項目。 |
| [core_audio_m3_requirements.md](core_audio_m3_requirements.md) | **核心主線 M3 Audio 開發要求**：定義 Core 與 POC 在 Audio HAL 的職責劃分、API 規範與 Pi 5 硬體交付契約。 |

## 與 PM Handoff 的職責分工

- `docs/specs/`：**永久全域規範**（專案全程生效之技術準則與驗收憲章）。
- `docs/pm_handoff/`：**階段性交接與合約流水帳**（各 Milestone 階段的 CONTRACT、ACK 與 `history/` 歸檔）。
