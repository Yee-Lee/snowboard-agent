# M4b Local LLM POC

## 📖 專案簡介 (Overview)
M4b Local LLM POC 是一個針對 **Raspberry Pi 5 (4GB)** 邊緣運算環境的大型語言模型概念驗證專案。

本專案旨在現有的產品架構下，探索並驗證合適的本機端 LLM 推論引擎（如 LiteRT-LM、llama.cpp 等）與輕量化開源模型（參數 ≤ 3B）。透過嚴謹的生命週期管理與資源監控，實現完全離線、低延遲且高度穩定的自然語言意圖理解與生成能力。

## 🎯 核心目標 (Core Objectives)

本 POC 專案聚焦於以下三大核心維度的技術驗證：

1. **Runtime & Model (運行環境與模型驗證)**
   - 確立可 100% 離線運行的推論引擎與依賴套件。
   - 評估合適的小型化模型（如 Gemma-2、Qwen2.5 等）與量化技術（INT4 / INT8 / GGUF），確保在 Raspberry Pi 5 資源受限的環境下兼顧推論速度與記憶體餘裕。
   
2. **Persistent Child Protocol (常駐子行程通訊協定)**
   - 建立穩健的跨行程通訊（IPC）機制與狀態隔離。
   - 支援完整的生命週期控制：包含快速啟動就緒（READY handshake）、超時控制（Timeout）、協同中斷（Cooperative Cancel）以及防止僵屍行程殘留的強制終止（Force Abort）。
   - 保證嚴格的歷史隔離（History Isolation），確保每次對話狀態獨立，無潛在的記憶體污染。

3. **Resource & Thermal Budget (資源與散熱管理)**
   - 確保在極端條件下與語音模組 (ASR + TTS) 同時常駐時，記憶體佔用 (Peak RSS) 嚴格控制在 4GB 硬體的安全範圍內。
   - 進行長時間壓力測試 (Soak Test)，確保 CPU 溫度控制在 80°C 以下，不發生熱降頻 (Thermal throttling)。

## 🚀 專案里程碑 (Milestones)

為確保評估過程的客觀性與系統穩定性，開發流程依序分為以下幾個主要里程碑：

- **M0: Readiness**
  - 基礎環境盤點、測試工具就緒與基準授權確認。
- **M1: Candidate Freeze**
  - 確立候選組合（精確鎖定 Runtime、模型、量化格式與版本）及測試腳本凍結。
- **M2: Pre-screen & Compatibility**
  - 在 Ubuntu 工作站進行快速效能初篩與相容性檢測，篩選出最終決選候選名單。
- **M3: Pi 5 Integration (LLM-only)**
  - 於 Raspberry Pi 5 實機進行單獨的 LLM 效能測試、常駐協定與極端中斷驗證。
- **M4: Combined Validation**
  - 結合語音模組進行全系統整合測試，驗證雙常駐情境下的資源分配與散熱穩定性。

## ⚙️ 系統需求 (Target Environment)

- **硬體平台**: Raspberry Pi 5 (4GB)
- **作業系統**: Debian 13 (Ubuntu 24.04 作為前置初篩與測試平台)
- **網路需求**: 完全離線 (Offline) 運行，無外部 API 依賴
