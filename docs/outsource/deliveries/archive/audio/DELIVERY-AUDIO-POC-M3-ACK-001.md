# Core Team → POC Audio Team: M3 Audio HAL Contract Acceptance

* **Delivery ID**: `DELIVERY-AUDIO-POC-M3-ACK-001`
* **Reference**: `audio_m3_contract_handoff_draft.md` v0.1
* **Status**: `Accepted with Conditions`
* **Core Team baseline branch**: `dev_agent_m3`
* **Date**: 2026-08-08

---

## 採用聲明

Core Team 正式採用 `audio_m3_contract_handoff_draft.md` v0.1 作為 **M3 Audio HAL 設計輸入**。

本文件與現有設計（`docs/implement/ch02a_core_hal.md`、`docs/implement/ch10_config.md`）核對結果全數一致，無架構衝突，可直接作為 M3 Audio real backend 實作的邊界依據。

---

## 一致性確認

| Contract 項目 | 現有產品設計對應 | 結果 |
|---|---|---|
| `start()` / `stop()` / `frames() -> AsyncIterator[bytes]` | `ch02a_core_hal.md` §2a.2 Protocol | ✅ 一致 |
| `play(pcm: AsyncIterator[bytes])` 完整消費 | `ch02a_core_hal.md` §2a.2 Protocol | ✅ 一致 |
| 16 kHz、mono、16-bit LE、20 ms frame | `ch10_config.md` `AudioConfig` 預設值 | ✅ 一致 |
| 同一 instance 只有一個 active iterator | `ch02a_core_hal.md` §2a.2 獨佔契約 | ✅ 一致 |
| stop 後無殘留 stream / task / device | `ch02a_core_hal.md` §2a.1 lifecycle | ✅ 一致 |
| HAL 不進 VAD / ASR，責任邊界清晰 | `ch02a_core_hal.md` 範圍邊界 | ✅ 一致 |
| Lazy factory / mock / null / alsa 分開 | `ch02a_core_hal.md` §2a.1 Factory | ✅ 一致 |
| Pi 5 + INMP441 + MAX98357A + I2S + `googlevoicehat-soundcard` | M3 real backend 目標（新增至文件） | ✅ 採用 |

---

## 採用條件（Pending Items）

下列三項不阻擋 M3 API 設計與實作開始，但 **Core Team M3 delivery SHA 釋出前** 須由 POC Audio 團隊先行確認：

| # | 項目 | 影響 | 責任方 |
|---|---|---|---|
| P1 | **Native PCM capability matrix**：Pi 5 + I2S 在 16 kHz / mono / 16-bit 的可行性，含 rate、channel、format matrix、xrun 行為與 lifecycle evidence | 若 16 kHz target 不可行，須提出 change request 後雙方同步修訂 `AudioConfig` 預設值與 cross-validation 規則 | POC Audio Tester |
| P2 | **實體裝置 identifier**：Pi 的 ALSA card/device identifier、driver config hash、接線圖與供電確認 | 阻礙可重現的 Pi test command；不進 generic source，以 local config override 傳遞 | POC Audio Tester / User |
| P3 | **TTS output PCM format**（rate / channels / bit depth / chunk behavior / fixture） | Output sample rate 待 M4b TTS winner 確定後 cross-validate；M3 Output API 先以 configurable 方式實作，不做 runtime resample | POC TTS / M4b |

---

## Core Team M3 完成後將回交下列產出

M3 產品驗收通過後，Core Team 將提供：

1. **完整 40-character commit SHA**（source、tests、文件均可由該 SHA 取得）
2. **Pi 5 安裝、driver/device、config 與執行命令**（需含 `googlevoicehat-soundcard` overlay 設定）
3. **自動化驗收 evidence**：Input PCM/frame timing、Output PCM 完整消費、start/stop/reopen、invalid device fallback/capability=false、cleanup 無殘留
4. **已知限制**：buffering、I2S shared-clock、xrun、ownership 限制

POC Audio Tester 以該 SHA 進行 POC M3 integration 驗收；若需修改 API、PCM contract 或 lifecycle 語意，須雙方先提出並核准 change request 後再更新文件版本。

---

## 請 POC Audio 團隊執行

1. 將 `audio_m3_contract_handoff_draft.md` 版本由 `DRAFT / NOT ACCEPTED` 更新為 `v1.0 / Accepted`，並標注本 Delivery ID `DELIVERY-AUDIO-POC-M3-ACK-001`。
2. 盡快提供 P1 Native PCM capability matrix（不阻礙 Core Team M3 開始，但應在 M3 驗收前完成）。
3. 提供 P2 實體裝置 identifier 供 M3 Pi test 使用。
4. P3 TTS format 待 M4b 另行通知。
