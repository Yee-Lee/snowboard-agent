# Snowboard Agent Runbooks

本目錄收錄 Snowboard Agent 各 Milestone 之標準操作手冊（Runbooks），供開發者、測試人員及設計人員依循標準流程進行開發環境建置、硬體接線與驗收測試。

---

## 📑 Milestone Runbooks 索引

| Milestone | 檔案連結 | 主要範疇 | 驗收方式 |
| :--- | :--- | :--- | :--- |
| **M1** | [`m1-development.md`](m1-development.md) | **核心架構與基礎設施**<br>(EventBus, State Machine, Supervisor, Shutdown) | 純 Python 無硬體主機端單元測試 |
| **M2** | [`m2-development.md`](m2-development.md) | **Mock 認知與意圖垂直切片**<br>(Perception, Intent Reasoner, Action, Mock HAL) | Deterministic Workers 與 Session 流程測試 |
| **M3** | [`m3-development.md`](m3-development.md)<br>實體驗收以 [`m3_rpi_validation.md`](m3_rpi_validation.md) 為準 | **Raspberry Pi 5 HAL 與實體硬體驗收**<br>(Audio I2S, Display SPI, Camera CSI, GPIO/Button) | 27 個 DEV 單元測項 + 20 個樹莓派實體硬體測試卡 |
| **M4 起共用 Candidate Gate** | [`candidate_hardware_gate.md`](candidate_hardware_gate.md) | **Pi 開發收斂與單一 frozen SHA**<br>(pre-candidate Pi loop、Python matrix、preflight、minimal result / raw log) | Pi working-tree convergence + 3.11 / 3.12 / 3.13 candidate matrix + 單一部署 runtime硬體驗收 |
| **M4A Developer Pi 診斷** | [`m4a_developer_pi_diagnostic.md`](m4a_developer_pi_diagnostic.md) | **送審前真實 Audio 開發收斂**<br>(fresh device/product、offline ASR/TTS/ALSA、cleanup) | Pi 直接修正至 Diagnostic Pass、單次同步回工作站；不取代 Tester acceptance |

---

## 🛠️ 基本操作原則

1. **Milestone 隔離**：各階段 Runbook 清楚定義該 Milestone 的範圍 (Scope) 與非目標 (Non-goals)。
2. **環境隔離**：所有硬體驗證命令必須於獨立之虛擬環境（包含系統套件存取 `--system-site-packages`）中執行。
3. **零憑證洩漏**：任何包含個人路徑、密鑰或敏感資訊之設定檔（如 `config.m3.local.yaml`）禁止提交至 Git。
4. **可重現性**：Developer working-tree diagnostic 以 base 40-character SHA、完整 task paths、
   patch bytes／SHA-256及標準命令重現；正式硬體驗收只以 clean exact candidate SHA 與
   標準測試命令重現。兩者不得互換或沿用結果。
5. **Pi 開發、candidate 驗收**：Pi 耦合工作先在隔離的 Pi checkout 直接修正並測到全綠，
   再以相同 base 與 patch digest 單次同步回工作站建立 candidate。正式 portable matrix、
   freeze 與 clean exact-SHA Pi acceptance 仍在 candidate 後執行；diagnostic 不得當成正式 Pass。
