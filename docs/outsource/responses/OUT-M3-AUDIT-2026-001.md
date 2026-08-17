# 回覆：OUT-M3-AUDIT-2026-001

## 基本資訊

- **階段**：commit 前 worktree 複驗；final candidate 尚未建立。
- **Branch**：`dev_agent_m3`。
- **目前 HEAD**：`d81601789ef40aeccd01dd8d4b9db67a01d76163`；本回覆、程式與
  regression 尚未提交，因此 **Response HEAD / 最終被測 implementation SHA：Pending**。
- **既有 Pi bundle implementation SHA**：
  `cab627705c341d0058e0c395e96d0be10c4c4239`；因本輪將修改 `src/` / `tests/`，
  不作為新候選的 acceptance evidence，commit 後必須依流程重跑。
- **Comparison baseline**：`c5906f879ab9dd5d1080f92213e7eefbe0b4a1e6`。
- **架構／dependency 變更**：無。
- **Config 變更**：除錯期間曾由 BCM23 改為 BCM27，之後已恢復 BCM23；目前本機
  `config.m3.local.yaml` SHA-256 為
  `4d16d1a37007fcf29daebaf2d39c6ce427597bede0ccb0c2c0a396e582b0c7f7`。
- **已知限制**：觸發 `c545de6ff389b56596fb7c2bb04bc3636a5863d9` 的原始 terminal
  log、當時完整命令、exception、kernel / libgpiod版本、config checksum及
  HEAD / worktree snapshot 均不可恢復；不得據此宣稱已證實 `pinctrl-rp1` 缺陷。

## 可由 repository 證明的事實

1. `a9a1ed47b50ce62ce5275009373692da41f99754` 於 2026-08-17 00:28:19
  （台北時間）提交 Audio hang 修正。
2. `c545de6ff389b56596fb7c2bb04bc3636a5863d9` 於 08:08:59 提交；diff 只讓
   `sbd.core.gpio.gpiod.driver.GpiodGPIO` 在 `debounce_ms == 0` 時省略
   `debounce_period`，正值路徑不變。commit subject 中的硬體歸因不是可驗證證據。
3. `6e1fe458cc5ed5700ad0c24cc1b5bf35fc771b22` 與
   `cab627705c341d0058e0c395e96d0be10c4c4239` 分別於 08:15:52、08:21:28
   新增互動式 Button runner與其餘硬體 runner。
4. 既有 `logs/button.xml` timestamp 是約 08:23，且包含五個 Button nodes；
   `c559e5cf65d20676696293f06f1e5bc2afd02ae6` 於約 08:51 提交 20-card bundle。
5. 該 bundle 記錄 Raspberry Pi 為 aarch64、Linux 6.12.47+rpt-rpi-2712、
   Python 3.13.5、gpiod 2.2.0，並記錄上述 BCM23 config checksum。這只能描述
   `cab627...` bundle，不能替新候選背書。

## 除錯時序：事後人員紀錄

以下來自當時 Developer / operator 的事後紀錄，因原始 log 遺失，不能提升為原始證據：

- Audio 修正後，以實體 BCM23 按鈕重測時，測試等待事件逾時；另行使用未傳
  `debounce_ms` 的 `test_edge.py` 可收到事件，因此一度錯誤推論為硬體 debounce問題。
- 約 08:08 依該推論建立 `c545de6...`。
- 約 08:18 才發現 `config.m3.local.yaml` 曾為 `auto_button.py` loopback 改成 BCM27，
  但使用者實際按的是 BCM23；恢復 BCM23 後才進行後續 Button重測。
- 因缺少原始 command / log，無法證明 zero-debounce change 是該次 Button PASS 的必要
  條件；可確認的設定污染才是 Pin 23 操作與 Pin 27 listener不一致的直接原因。

## 技術判定與產品影響

- `pinctrl-rp1` 在正值 hardware debounce 下漏事件目前只能列為**未證實的事後推論**；
  本回覆不再把它描述成 root cause或現行 reproduction。
- `c545de6...` 定位為 defensive change：避免 libgpiod 收到無意義的零長度
  `debounce_period`。既有 M3 Button 50 ms與 GPIO loopback至少 20 ms路徑不受影響；
  沒有證據顯示任何既有 M3 Test ID 必須靠零值路徑才通過。
- Portable regression 直接驗證零值省略及 50 ms原值傳遞；結果與完整命令見
  `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/retest-audit-20260817/portable-precommit.md`。

## Button runner 能力邊界

- 早期 `button.xml` 只有 `M3-BTN-002`，是單卡 `-k test_m3_btn_002` 執行覆寫同一
  JUnit路徑造成；現存 `cab627...` bundle 的 `button.xml` 已包含五個 nodes。
- `scripts/run_m3_button.sh` 可把五個 Button nodes放入同一 pytest命令及同一 JUnit；
  它只以當時 `git rev-parse HEAD` 設定候選值，本身**不會**拒絕 dirty worktree、驗證
  外部指定 SHA，亦不能單獨證明 manual cards、manifest與其他 runner屬同一次 run。
- 新 candidate 仍須走 workflow 的 protected-path clean check、exact-SHA、全新 run ID、
  evidence index與 Tester reconciliation；不得沿用 `cab627...` 的舊卡片宣告 PASS。

## 交付與證據定位

- 原始證據缺失及替代證據索引：
  `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/retest-audit-20260817/README.md`
- Commit 前 portable reproduction：
  `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/retest-audit-20260817/portable-precommit.md`
- 舊 bundle identity：
  `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/manifest.json`
- 新候選 SHA、README / manifest / results / cards 對齊：**Pending**；須先通過 Tester 的
  commit 前審查，再展示 commit proposal並取得 USER明確同意，commit 後才可重錄。
