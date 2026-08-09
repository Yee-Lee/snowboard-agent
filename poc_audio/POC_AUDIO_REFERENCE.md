# POC Audio 參考資源索引 (Agent Reference)

為了避免未來的 Agent 反覆進入 `poc_audio/` 爬取資訊，本文件已先將 `poc_audio/` 內有參考價值的資源列舉如下：

## 1. 測試腳本 (`poc_audio/tools/`)
這些 bash 腳本是 Audio 團隊在 Pi 上執行測試與環境驗證的工具。我們在開發 LLM 時，可以參考它們的邏輯（例如如何驗證 Pi 5 環境、如何檢查 Git Clean 狀態、如何透過 SSH 執行指令）：
* `environment_pre_test.sh`: 驗證本地環境與 Pi 目標硬體（檢查 SSH 連線、Pi 5 架構、Git SHA 是否一致、硬體資源狀態等）。
* `m0_remote_readiness.sh`: 驗證遠端指令生命週期、Cancel 機制與檔案傳輸 (checksum-preserving)。
* `m1_native_audio_capability.sh`: 驗證 ALSA 裝置與硬體處理能力（純測試，無聲音檔案保留）。

## 2. 成果與日誌 (供參考目錄結構)
* `poc_audio/evidence/`: 存放從 Pi 回收的 sanitized evidence（過濾敏感資訊後的資源或執行紀錄）。
* `poc_audio/deliveries/`: 存放對外的最終發布或 manifest 檔案。

**結論**：後續在編寫 LLM 測試腳本 (`poc_llm/tools/`) 時，可以直接查閱 `poc_audio/tools/` 內的 `.sh` 檔案作為撰寫 Bash / SSH 遠端測試腳本的樣板，無需重新發明輪子。
