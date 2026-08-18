# Snowboard Agent Runbooks

本目錄收錄 Snowboard Agent 各 Milestone 之標準操作手冊（Runbooks），供開發者、測試人員及設計人員依循標準流程進行開發環境建置、硬體接線與驗收測試。

---

## 📑 Milestone Runbooks 索引

| Milestone | 檔案連結 | 主要範疇 | 驗收方式 |
| :--- | :--- | :--- | :--- |
| **M1** | [`m1-development.md`](m1-development.md) | **核心架構與基礎設施**<br>(EventBus, State Machine, Supervisor, Shutdown) | 純 Python 無硬體主機端單元測試 |
| **M2** | [`m2-development.md`](m2-development.md) | **Mock 認知與意圖垂直切片**<br>(Perception, Intent Reasoner, Action, Mock HAL) | Deterministic Workers 與 Session 流程測試 |
| **M3** | [`m3-development.md`](m3-development.md)<br>實體驗收以 [`m3_rpi_validation.md`](m3_rpi_validation.md) 為準 | **Raspberry Pi 5 HAL 與實體硬體驗收**<br>(Audio I2S, Display SPI, Camera CSI, GPIO/Button) | 27 個 DEV 單元測項 + 20 個樹莓派實體硬體測試卡 |
| **M4 起共用 Candidate Gate** | [`candidate_hardware_gate.md`](candidate_hardware_gate.md) | **Portable-first 與單一 frozen SHA**<br>(Python matrix, preflight, minimal result / raw log) | 3.11 / 3.12 / 3.13 candidate matrix + 單一部署 runtime硬體驗收 |

---

## 🛠️ 基本操作原則

1. **Milestone 隔離**：各階段 Runbook 清楚定義該 Milestone 的範圍 (Scope) 與非目標 (Non-goals)。
2. **環境隔離**：所有硬體驗證命令必須於獨立之虛擬環境（包含系統套件存取 `--system-site-packages`）中執行。
3. **零憑證洩漏**：任何包含個人路徑、密鑰或敏感資訊之設定檔（如 `config.m3.local.yaml`）禁止提交至 Git。
4. **可重現性**：所有硬體驗證結果必須能透過指定之 40 字元 Git Commit SHA 與標準測試命令完整重現。
5. **候選先於硬體**：自 M4 起在candidate freeze前完成一次portable matrix；日常push只跑主要版本與affected tests，debug結果不得當成正式Pass。
