# AI 專案入口

Snowboard 是運行於 Raspberry Pi 5 的全離線語音助理，以 OLED 顯示本機狀態，核心整合 ASR、LLM、TTS、視覺與硬體 HAL。

目前座標：Display POC 的工作準備（P0）完成；Immutable Candidate Freeze（P1）待執行，Core M3 尚未解鎖。進度與下一步只以 `docs/poc/milestone_plan.md` 為準。

架構原則只預載標題：P1 Core = 契約 + Library Adapter；P2 契約依實際使用情境；P3 Adaptor 只承擔對外通道；P4 介面允許未來跨 process；P5 Worker 內部降級、例外外洩為最後手段。完整定義按需查 `docs/arch.md` §1.3。

## 按需索引

- 進度、未完成工作：`docs/poc/milestone_plan.md`
- 架構、狀態機、契約：`docs/arch.md`
- 外部團隊原始交付與審查：`docs/pm_handoff/`（唯讀參考，不直接改寫）
- Display 實作設計：`src/sbd/core/display/display_arch.md`
- POC 實機流程、證據：`poc_display/README.md`、`poc_display/evidence/`

## AI 工作方式

- 不預讀整個 `docs/` 或 `docs/pm_handoff/`。先用 `rg` 搜尋任務關鍵字，再局部讀取命中段落；只有上下文不足時才擴大範圍。
- 判斷現況先看里程碑 checkbox，再以程式、測試與 evidence 驗證；外部交付文件不能取代當前狀態。
- 保留工作樹既有變更；修改前先看 `git status`，不要覆寫無關成果。
