# Developer & Designer Response to Carry-over Feedback (CR-M1-II)

* **Handoff ID** : `PM-OUT-260806-003-m1-test-platform-scope`
* **Legacy ID** : `PM-OUT-2026-001-R2`
* **Related Feedback** : `CR-M1-II`
* **Tested Implementation SHA** : `af890249d8634df11b1a30a27aaee1720f5a8b67`
* **Status** : `Resolved & Consensus Confirmed`
* **Architecture Change** : `No`

---

## 1. 測試平台矩陣共識逐項確認 (Mandatory 4-Point Consensus)

開發團隊（Designer / Developer）已明確確認並於規範文件中完成以下四大共識對齊：

1. **Windows 平台範圍**：Windows 平台僅要求 portable 純 Python / mock / config 與適用的 subprocess 測試（如 stream/pipe readiness）。
2. **POSIX Signal 驗證撤回**：Windows 專屬或不適用的 POSIX `SIGINT` / `SIGTERM` 驗證正式撤回，不再要求於 Windows 平台執行。
3. **Production 架構不變聲明**：絕不為了配合 Windows POSIX signal 測試而修改 production signal architecture。
4. **權威平台定位**：Linux / Raspberry Pi 仍是 POSIX process signal、native lifecycle 與正式 runtime 驗證的權威平台。

---

## 2. Action Items 執行與對應現況

| ID | Priority | Description & Action | Status / Alignment |
| --- | --- | --- | --- |
| `CR-M1-II-001` | Blocking | 依新矩陣提交被測 implementation SHA 之正式結果 | **Pass** (Windows portable suite 0 Fail; Linux Python 3.11 M1 entrypoint, full suite 與 POSIX signal 節點全數 0 Fail；日誌已 commit) |
| `CR-M1-II-002` | Verified | `/etc/hosts` fixture 替換為 `tmp_path` | **Pass** (已由內部於 Windows / Python 3.11 驗證 `16 passed`，且具備跨平台 `sample_rate` 檢測能力) |
| `CR-M1-II-003` | High / Scope Correction | 逐項確認四點共識；於文件拆分 portable 與 Linux process 平台；維持 production signal 架構不變 | **Pass** (開頭已逐項確認 4 點共識；`docs/test_spec.md` 新增 `POSIX-PROC` / `DEV-PROC` / `DEV-PY311` 分流；`docs/milestone.md` 及 `docs/milestones/M1.md` 對齊完成；無 Production 架構修改) |
| `CR-M1-II-005` | High | 修正 response / delivery / evidence 之被測 SHA 與索引 | **Pass** (正式檔對齊 `PM-OUT-260806-003-m1-test-platform-scope`；被測 SHA 為 `af890249d8634df11b1a30a27aaee1720f5a8b67`) |
| `CR-M1-II-004` | Advisory | 保留 wildcard removal；說明 nested pytest 延後最佳化 | **Pass** (保留 wildcard removal，full suite 正確收斂為 167 精確節點；nested pytest 最佳化不阻擋產品完整度) |

---

## 3. 驗證命令與結果摘要

### 1. M1 Milestone Entrypoint 驗證
- **命令**：
  ```bash
  PYTHONPATH=src python3 -m pytest -p no:cacheprovider -q tests/milestones/test_m1_foundation.py
  ```
- **結果**：`1 passed in 5.40s` (0 Fail)

### 2. Full Suite Regression 驗證 (Linux 權威平台含 POSIX signals)
- **命令**：
  ```bash
  PYTHONPATH=src python3 -m pytest -p no:cacheprovider -q
  ```
- **結果**：`167 passed in 9.66s` (0 Fail, 0 Skip, 0 Blocked)

### 3. Windows Portable Suite 驗證 (Deselect Linux POSIX signal nodes)
- **結果**：`16 passed in 1.20s` (0 Fail)

---

## 4. 相關交付與證據路徑

* **Response** : [`docs/outsource/responses/CR-M1-II.md`](file:///home/yee/workspace/snowboard-agent/docs/outsource/responses/CR-M1-II.md)
* **Delivery** : [`docs/outsource/deliveries/DELIVERY-M1-CR-M1-II.md`](file:///home/yee/workspace/snowboard-agent/docs/outsource/deliveries/DELIVERY-M1-CR-M1-II.md)
* **Evidence** : `docs/outsource/evidence/DELIVERY-M1-CR-M1-II/`
